from larpixdaq.routines import Routine
import statistics as stats

start_dac=255
end_dac=100

def _test_pulse(controller, send_data, send_info, *args):
    '''
    test_pulse(chip, pulse_ampl, n_pulses)

    Issues ``n_pulses`` of amplitude ``pulse_ampl`` to each channel on the
    specified chip

    '''
    chip_key = args[0]
    pulse_ampl = int(args[1])
    n_pulses = int(args[2])

    for channel in range(32):
        send_info('pulsing ch {}'.format(channel))
        controller.enable_testpulse(chip_key, channel_list=[channel], start_dac=start_dac)
        npackets = 0
        packet_adcs = []
        for pulse in range(n_pulses):
            try:
                controller.issue_testpulse(chip_key, pulse_ampl, min_dac=end_dac)
            except ValueError:
                controller.enable_testpulse(chip_key, channel_list=[channel], start_dac=start_dac)
                controller.issue_testpulse(chip_key, pulse_ampl, min_dac=end_dac)
            packet_adcs += controller.reads[-1].extract('adc_counts',chip_key=chip_key,channel=channel)
            npackets += len(controller.reads[-1])
        controller.disable_testpulse(chip_key, channel_list=[channel])
        if len(packet_adcs) >= 2:
            send_info('ch {} - mean {} - stdev {} - med {} - N {} - total N {}'.format(
                channel, stats.mean(packet_adcs), stats.stdev(packet_adcs), stats.median(packet_adcs), len(packet_adcs), npackets
                ))
        else:
            send_info('ch {} - mean None - stdev None - med None - N {} - total N {}'.format(
                channel, len(packet_adcs), npackets
                ))

    to_return = 'success'
    return controller, to_return

test_pulse = Routine('test_pulse', _test_pulse, ['chip','pulse_ampl','n_pulses'])

registration = {'test_pulse': test_pulse}
