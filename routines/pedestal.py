from larpixdaq.routines import Routine
import copy
import statistics as stats

run_time = 0.1
global_threshold = 0
sample_cycles = 255

def _pedestal(controller, send_data, send_info, *args):
    '''
    pedestal(chip)

    Quickly sets threshold to 0 on each channel to force digitizations.
    Temporarily modifies channel mask and sample cycles for a cleaner measurement.

    '''
    chip_key = args[0]
    chip = controller.get_chip(chip_key)

    orig_config = copy.deepcopy(chip.config)

    controller.disable(chip_key)
    chip.config.global_threshold = global_threshold
    chip.config.sample_cycles = sample_cycles
    controller.write_configuration(chip_key)

    for channel in range(32):
        send_info('pedestal ch {}'.format(channel))
        controller.enable(chip_key, [channel])
        controller.io.empty_queue()
        controller.run(run_time,message='pedestal ch {}'.format(channel))
        controller.disable(chip_key)
        adcs = controller.reads[-1].extract('adc_counts', chip_key=chip_key, channel=channel)
        if len(adcs) > 0:
            send_info('ch {} - mean {} - stdev {} - med {} - N {}'.format(channel, stats.mean(adcs), stats.stdev(adcs), stats.median(adcs), len(adcs)))

    chip.config = orig_config
    controller.write_configuration(chip_key)

    to_return = 'success'
    return controller, to_return

pedestal = Routine('pedestal', _pedestal, ['chip'])

registration = {'pedestal': pedestal}
