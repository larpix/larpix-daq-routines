from larpixdaq.routines.routines import Routine
import os

config_dir=os.path.join(os.path.dirname(__file__), '../configs/')

def _load_configuration(controller, send_data, send_info, *args):
    '''
    load_configuration(configuration_name)

    Load and write configuration to a specified chip, verifies after writing

    '''
    chip = args[0]
    config_name = args[1]
    to_return = ''
    try:
        send_info('checking for config in {}'.format(config_dir))
        controller.get_chip(chip).config.load(os.path.join(config_dir, config_name))
        controller.write_configuration(chip)
        to_return = 'success'
    except IOError:
        try:
            send_info('checking for built-in config {}'.format(config_name))
            controller.get_chip(chip).config.load(config_name)
            controller.write_configuration(chip)
            to_return = 'success'
        except IOError:
            send_info('no config {} found'.format(config_name))
            to_return = 'error'
    if to_return != 'error':
        valid, diff_registers = controller.verify_configuration(chip)
        if not valid:
            to_return = 'error'
            send_info('could not verify: {}'.format(diff_registers))
    return controller, to_return

load_configuration = Routine('load_configuration', _load_configuration, ['chip','config_name'])

registration = {'load_configuration': load_configuration}
