from larpixdaq.routines import Routine
import copy
from larpix.larpix import Configuration

quick_run_time = 0.1

def _leakage(controller, send_data, send_info, *args):
    '''
    leakage(chip, run_time)

    Measures leakage rate on a given chip by disabling periodic resets. Leakage
    current can be calculated as (rate_leakage - rate_nom) * threshold where
    rate_leakage is the trigger rate during this routine, rate_nom is the nominal
    trigger rate, and threshold is the trigger threshold.

    '''
    chip_key = args[0]
    run_time = float(args[1])

    chip = controller.get_chip(chip_key)

    orig_config = copy.deepcopy(chip.config)
    chip.config.periodic_reset = 0
    controller.write_configuration(chip_key, Configuration.test_mode_xtrig_reset_diag_address)

    send_info('start leakage routine')
    controller.io.empty_queue()
    controller.run(run_time,message='leakage {}'.format(chip_key))
    packets = list(filter(lambda x: x.chip_key == chip_key, controller.reads[-1]))
    for channel in range(32):
        channel_packets = list(filter(lambda x: x.channel_id == channel, packets))
        send_info('rate {}: {} Hz'.format(channel, len(channel_packets)/run_time))
    chip.config = orig_config
    controller.write_configuration(chip_key)

    to_return = 'success'
    return controller, to_return

leakage = Routine('leakage', _leakage, ['chip', 'run_time'])

registration = {'leakage': leakage}
