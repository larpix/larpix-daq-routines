from larpixdaq.routines import Routine
import copy
from larpix.larpix import Configuration

quick_run_time = 0.1

def _rough_leakage(controller, send_data, send_info, *args):
    '''
    rough_leakage(chip, run_time, parallelize)

    Measures rough_leakage rate on a given chip by disabling periodic resets and
    increasing the global_threshold to 125 and pixel trims to 31. Requires knowing
    the channel pedestal to determine the rough_leakage current.

    chip: chip key to run test on

    run_time: period in seconds to measure leakage rate for

    parallelize: boolean flag to measure channels one-by-one (false) or all at one (true)

    '''
    chip_key = args[0]
    run_time = float(args[1])
    parallelize = bool(args[2])

    chip = controller.get_chip(chip_key)

    orig_config = copy.deepcopy(chip.config)
    chip.config.periodic_reset = 0
    chip.config.global_threshold = 125
    chip.config.pixel_trim_thresholds = [31]*32
    if not parallelize:
        chip.config.channel_mask = [1]*32

    registers_to_write = [Configuration.global_threshold_address] + \
        Configuration.pixel_trim_threshold_addresses + \
        [Configuration.test_mode_xtrig_reset_diag_address]
    if not parallelize:
        registers_to_write += Configuration.channel_mask_addresses
    controller.write_configuration(chip_key, registers_to_write)

    send_info('start rough_leakage routine')
    controller.io.empty_queue()
    iter_idx = 0
    while True:
        if not parallelize:
            # prep channel mask for channel to test
            chip.config.channel_mask = [1]*32
            chip.config.channel_mask[iter_idx] = 0
            controller.write_configuration(chip_key, Configuration.channel_mask_addresses)
        # collect data for the specified run time
        send_info('run rough_leakage {}'.format(iter_idx))
        controller.run(run_time,message='rough_leakage {} {}'.format(chip_key, iter_idx))

        # log number of triggers received for each channel
        packets = list(filter(lambda x: x.chip_key == chip_key, controller.reads[-1]))
        for channel in range(32):
            channel_packets = list(filter(lambda x: x.channel_id == channel, packets))
            print_str = 'rate {}: {} Hz'.format(channel, len(channel_packets)/run_time)
            if parallelize:
                send_info(print_str)
            elif len(channel_packets) > 0 or channel == iter_idx:
                send_info(print_str)

        # check next channel or end loop
        if not parallelize and iter_idx < 31:
            iter_idx += 1
        else:
            break

    chip.config = orig_config
    controller.write_configuration(chip_key)

    to_return = 'success'
    return controller, to_return

rough_leakage = Routine('rough_leakage', _rough_leakage, ['chip', 'run_time'])

registration = {'rough_leakage': rough_leakage}
