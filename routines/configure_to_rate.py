from larpixdaq.routines import Routine
from larpix.larpix import Configuration, Packet
from collections import defaultdict
import time
import os

out_dir=os.path.join(os.path.dirname(__file__), '../configs/')
out_filename_fmt='%y-%m-%d_%H-%M-%S_{chip_key}.json'
quick_run_time = 0.1

def log_msg(message, chip_key=None):
    if chip_key:
        return 'configure_to_rate - {} - {}'.format(chip_key, message)
    return 'configure_to_rate - {}'.format(message)

def npackets_by_channel(packets):
    return_dict = defaultdict(int)
    for packet in packets:
        if packet.packet_type == Packet.DATA_PACKET:
            return_dict[packet.channel_id] += 1
    return return_dict

def flush_queue(controller):
    controller.io.empty_queue()

def _configure_to_rate(controller, send_data, send_info, *args):
    '''
    configure_to_rate(chip, rate, max_rate, global_start, trim_start, run_time)

    Modifies chip thresholds to insure that trigger rate is less than specified. Channels above ``max_rate`` will be disabled.
    '''
    chip_key = args[0]
    rate = float(args[1])
    max_rate = float(args[2])
    global_start = int(args[3])
    trim_start = int(args[4])
    run_time = float(args[5])

    chip = controller.get_chip(chip_key)
    threshold_registers = Configuration.pixel_trim_threshold_addresses + [Configuration.global_threshold_address]

    # Check for high rate channels with start values
    send_info('check for high rate channels')
    channel_mask_orig = chip.config.channel_mask
    disabled_channels = [channel for channel in range(32) if channel_mask_orig[channel] == 1]
    chip.config.global_threshold = global_start
    chip.config.pixel_trim_thresholds = [trim_start]*32
    controller.write_configuration(chip_key, threshold_registers)

    break_flag = False
    while not break_flag:
        break_flag = True
        flush_queue(controller)
        controller.run(run_time, message=log_msg('start check rate', chip_key))
        packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
        npackets = npackets_by_channel(packets)
        send_info('n packets: {}'.format(npackets))
        for channel,npacket in npackets.items():
            if npacket >= max_rate * run_time:
                disabled_channels += [channel]
                break_flag = False
        if not break_flag:
            controller.disable(chip_key, channel_list=disabled_channels)

    # Step down through global threshold settings
    send_info('start coarse global threshold scan')
    break_flag = False
    while not break_flag:
        flush_queue(controller)
        controller.run(quick_run_time, message=log_msg('coarse global check rate', chip_key))
        packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
        npackets = npackets_by_channel(packets)
        send_info('{} - n packets: {}'.format(chip.config.global_threshold, npackets))
        for channel,npacket in npackets.items():
            if npacket >= rate * quick_run_time:
                break_flag = True
        if all([channel in disabled_channels for channel in range(32)]):
            break_flag = True
        if not break_flag:
            try:
                chip.config.global_threshold -= 1
            except ValueError:
                break_flag = True
            finally:
                controller.write_configuration(chip_key, threshold_registers)
    send_info('end coarse global threshold scan')

    # Step back up with finer rate measurement
    send_info('start fine global threshold scan')
    break_flag = False
    while not break_flag:
        flush_queue(controller)
        controller.run(run_time, message=log_msg('fine global check rate', chip_key))
        packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
        npackets = npackets_by_channel(packets)
        send_info('{} - n packets: {}'.format(chip.config.global_threshold, npackets))
        if all([npackets[channel] < rate * run_time for channel in range(32)]):
            break_flag = True
        if not break_flag:
            try:
                chip.config.global_threshold += 1
            except ValueError:
                break_flag = True
            finally:
                controller.write_configuration(chip_key, threshold_registers)
    send_info('end fine global threshold scan')

    # Step down through trim threshold settings
    send_info('start coarse pixel trim threshold scan')
    break_flag = False
    completed_channels = [] + disabled_channels
    while not break_flag:
        skip_trim_adjustment = False
        flush_queue(controller)
        controller.run(quick_run_time, message=log_msg('coarse trim check rate', chip_key))
        packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
        npackets = npackets_by_channel(packets)
        send_info('n packets: {}'.format(npackets))
        for channel,npacket in npackets.items():
            if npacket >= rate * quick_run_time:
                completed_channels += [channel]
                skip_trim_adjustment = True
        if not skip_trim_adjustment:
            for channel in list(filter(lambda x: x not in completed_channels, range(32))):
                try:
                    chip.config.pixel_trim_thresholds[channel] -= 1
                except ValueError:
                    completed_channels += [channel]
            controller.write_configuration(chip_key, threshold_registers)
        else:
            controller.disable(chip_key, channel_list=completed_channels)
        if all([channel in completed_channels for channel in range(32)]):
            break_flag = True
    send_info('end coarse pixel trim threshold scan')

    # Step back up with finer rate measurement
    send_info('start fine pixel trim threshold scan')
    break_flag = False
    completed_channels = [] + disabled_channels
    controller.enable(chip_key, channel_list=list(filter(lambda x: x not in disabled_channels, range(32))))
    while not break_flag:
        flush_queue(controller)
        controller.run(run_time, message=log_msg('fine trim check rate', chip_key))
        packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
        npackets = npackets_by_channel(packets)
        send_info('n packets: {}'.format(npackets))
        for channel in range(32):
            if npackets[channel] < rate * run_time:
                completed_channels += [channel]
            else:
                try:
                    chip.config.pixel_trim_thresholds[channel] += 1
                except ValueError:
                    disabled_channels += [channel]
                    completed_channels += [channel]
        controller.disable(chip_key, channel_list=disabled_channels)
        controller.write_configuration(chip_key, threshold_registers)
        if all([channel in completed_channels for channel in range(32)]):
            break_flag = True
    send_info('end fine pixel trim threshold scan')

    # Check rate one last time
    send_info('check new rate')
    flush_queue(controller)
    controller.run(run_time, message=log_msg('fine trim check rate'))
    packets = filter(lambda x: x.chip_key == chip_key, controller.reads[-1])
    npackets = npackets_by_channel(packets)
    send_info('n packets: {}'.format(npackets))
    for channel,npacket in npackets.items():
        if npacket >= max_rate * run_time:
            disabled_channels += [channel]
    controller.disable(chip_key, channel_list=disabled_channels)
    controller.write_configuration(chip_key, threshold_registers)

    flush_queue(controller)
    controller.run(run_time, message=log_msg('fine trim check rate'))
    packets = list(filter(lambda x: x.chip_key == chip_key, controller.reads[-1]))
    send_info('{} Hz'.format(len(packets)/run_time))

    # Save config
    filename = time.strftime(out_filename_fmt).format(chip_key=chip_key)
    path = os.path.join(out_dir, filename)
    chip.config.write(path, force=True)

    to_return = path
    return controller, to_return

configure_to_rate = Routine('configure_to_rate', _configure_to_rate, ['chip', 'rate', 'max_rate', 'global_start', 'trim_start', 'run_time'])

registration = {'configure_to_rate': configure_to_rate}
