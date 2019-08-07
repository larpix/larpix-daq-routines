from larpixdaq.routines import Routine
import copy
from larpix.larpix import Configuration

quick_run_time = 0.1

def _rough_leakage(controller, send_data, send_info, *args):
    '''
    rough_leakage(chip, run_time)

    Measures rough_leakage rate on a given chip by disabling periodic resets and
    increasing the global_threshold to 125 and pixel trims to 31. Requires knowing
    the channel pedestal to determine the rough_leakage current.
    '''
    chip_key = args[0]
    run_time = float(args[1])

    chip = controller.get_chip(chip_key)

    orig_config = copy.deepcopy(chip.config)
    chip.config.periodic_reset = 0
    chip.config.global_threshold = 125
    chip.config.pixel_trim_thresholds = [31]*32

    controller.write_configuration(chip_key, \
        [Configuration.global_threshold_address] + \
        Configuration.pixel_trim_threshold_addresses + \
        [Configuration.test_mode_xtrig_reset_diag_address])

    send_info('start rough_leakage routine')
    controller.io.empty_queue()
    controller.run(run_time,message='rough_leakage {}'.format(chip_key))
    packets = list(filter(lambda x: x.chip_key == chip_key, controller.reads[-1]))
    for channel in range(32):
        channel_packets = list(filter(lambda x: x.channel_id == channel, packets))
        send_info('rate {}: {} Hz'.format(channel, len(channel_packets)/run_time))
    chip.config = orig_config
    controller.write_configuration(chip_key)

    to_return = 'success'
    return controller, to_return

rough_leakage = Routine('rough_leakage', _rough_leakage, ['chip', 'run_time'])

registration = {'rough_leakage': rough_leakage}
