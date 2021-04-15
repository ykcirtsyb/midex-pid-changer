#!/usr/bin/python3

import argparse
import json
import logging
import os, os.path
import sys
import pyudev
from time import sleep
import usb.core
import usb.util


PROGRAM_DESC = "Steinberg MIDEX product id updater"

###################################################################################################
###################################################################################################

MIDEX_VID = 0x0a4e    # Steinberg USB VID

TARG_PID = 0x1001
MIDEX_PIDs = [
    0x1000,
    0x1010,
    TARG_PID
  ]


logger = None
known_devs = []

###################################################################################################
# -g / --generate functions
###################################################################################################

def load_wireshark_packets(filepath):
  """Load FW data from json file exported from Wireshark

  Args:
      filepath (str): json file path

  Returns:
      list: list of dicts with frames
  """

  try:
    with open(filepath, 'r') as f:
      js_data = json.load(f)
      if len(js_data) < 1:
        err = f"load_wireshark_packets: '{filepath}' is empty or has bad format!"
        print(f"[ERROR] {err}")
        logger.error(err)
        return []

    data = []
    for index in range(2, len(js_data)):
      if js_data[index]['_source']['layers']['usb']['usb.src'] == "host" and "Setup Data" in js_data[index]['_source']['layers'].keys():
        try:
          item = js_data[index]['_source']['layers']['Setup Data']
          data.append(
            {
              'bmRequestType': int(item['usb.bmRequestType'], 16),
              'bRequest': int(item['usb.setup.bRequest']),
              'wValue': int(item['usb.setup.wValue'], 16),
              'wIndex': int(item['usb.setup.wIndex']),
              'wLength': int(item['usb.setup.wLength']),
              'data_fragment': tuple(map(lambda x: int(x, 16), item['usb.data_fragment'].split(':')))
            }
          )
        except KeyError as e:
          err = f'load_wireshark_packets: Dict key error: {e}!'
          print(f"[ERROR] {err}")
          logger.error(err)

          return []

  except FileNotFoundError:
    err = f"load_wireshark_packets: '{filepath}' doesn`t exist!"
    print(f"[ERROR] {err}")
    logger.error(err)
    return []

  return data

###################################################################################################

def create_new_fw_json(filepath, fw_data):
  if filepath != None:
    if isinstance(filepath, str):
      with open(filepath, 'w') as file:
        json.dump(fw_data, file, indent = 4)
      inf = f"create_new_fw_json: New FW file exported to '{filepath}'"
      print(f"[INFO] {inf}")
      logger.info(inf)

      return True
    else:
      err = f"create_new_fw_json: 'filepath' must be type of 'string' not '{type(filepath)}'"
      print(f"[ERROR]: {err}")
      logger.error(err)

      return False

###################################################################################################
###################################################################################################
# Normal run functions
###################################################################################################

def prepare_logger():
  global logger

  logger = logging.getLogger(__name__)
  logger.setLevel(logging.INFO)

  path = (os.path.dirname(os.path.realpath(__file__)))
  fh = logging.FileHandler(os.path.join(path, 'log.txt'))
  fh.setLevel(logging.INFO)

  formatter = logging.Formatter('%(asctime)s - [%(levelname)s]:\t%(message)s', datefmt='%d/%m/%Y %H:%M:%S')

  fh.setFormatter(formatter)
  logger.addHandler(fh)

###################################################################################################
    
def find_device_handle(vid, pid):
  """Find device and create its handler.
  If a list of multiple PIDs is entered, the device found first will be used.

  Args:
      vid (int/hex): MIDEX Vendor Id
      pid (int/hex/list): MIDEX Product Id or list of Ids

  Returns:
      handle: Device handle if it found, else None
  """

  if isinstance(pid, list):
    for id in pid:
      dev = usb.core.find(idVendor = vid, idProduct = id)
      if dev != None:
        break
  else:
    dev = usb.core.find(idVendor = vid, idProduct = pid)
  
  return dev

###################################################################################################

def load_fw_data_from_file(filepath):
  try:
    with open(filepath, 'r') as f:
      js_data = json.load(f)
      if len(js_data) < 1:
        err = f"'{filepath}' is empty or has bad format!"
        print(f"[ERROR] {err}")
        logger.error(err)
        return None

      return js_data

  except FileNotFoundError:
    err = f"'{filepath}' doesn`t exist!"
    print(f"[ERROR] {err}")
    logger.error(err)
    return None

###################################################################################################

def send_fw_data_to_device(device, fw_data):
  """Prepare and send data to the USB device

  Args:
      device (handle): USB device handler
      fw_data (list): FW data

  Returns:
      bool: True if all done, else False
  """

  if isinstance(fw_data, list):   
    for item in fw_data:
      try:
        device.ctrl_transfer(item['bmRequestType'], item['bRequest'], wValue=item['wValue'], wIndex=item['wIndex'], data_or_wLength=item['data_fragment'])
        sleep(0.01)
      except Exception as e:
        err = f'send_fw_data_to_device: {e}'
        print(f'[ERROR] {err}')
        logger.error(err)
        return False

    return True

  return False

###################################################################################################

def run(fw_data):
  dev = find_device_handle(MIDEX_VID, MIDEX_PIDs)
  if dev != None:

    desc = {"bus": dev.bus, "addr": dev.address, "pid": dev.idProduct}
    if not desc in known_devs:
      known_devs.append(desc)

      inf = f"New MIDEX found ({hex(dev.idProduct)}) - Bus {dev.bus} Device {dev.address}"
      print(inf)
      logger.info(inf)

      if dev.idProduct != TARG_PID: # if this device is not newest FW
        inf = "The firmware of this device will be updated first.."
        print(inf)
        logger.info(inf)

        # detach from kernel module, if it is used
        if dev.is_kernel_driver_active(0):
          dev.detach_kernel_driver(0)
          inf = "- detached from the Kernel"
          print(inf)
          logger.info(inf)
        else:
          inf = "- not used in the Kernel"
          print(inf)
          logger.info(inf)

        # try to update FW
        if send_fw_data_to_device(dev, fw_data):
          inf = "- update done"
          print(inf)
          logger.info(inf)
      else:
        inf = "The firmware of this device is up to date and will be used."
        print(inf)
        logger.info(inf)

###################################################################################################

def main():
  try:
    parser = argparse.ArgumentParser(description = PROGRAM_DESC)
    parser.add_argument("-f", "--file", action = "store", dest = "fw_file", type = str, help = "path to the MIDEX firmware file (json)")
    parser.add_argument("-g", "--generate", action = "store_true", dest = "generate", help = "generate new 'fw.json' from [-i] to [-o], default is False")
    parser.add_argument("-i", "--input", action = "store", default = None, dest = "input", type = str, help = "input file if generade mode")
    parser.add_argument("-o", "--output", action = "store", default = None, dest = "output", type = str, help = "output file if generade mode")
    args = parser.parse_args()


    if args.fw_file == None and args.generate == False:
      parser.print_help()
      sys.exit(0)


    if args.generate is True:
      if (isinstance(args.input, str) and len(args.input) > 1) and (isinstance(args.output, str) and len(args.output) > 1):
        prepare_logger()
        data = load_wireshark_packets(args.input)
        if data != []:
          create_new_fw_json(args.output, data)
      else:
        parser.print_help()

    else:

      if os.geteuid()  != 0:
        warn = "The script must run as root for this function!"
        print(warn)

        return

      prepare_logger()
      print(PROGRAM_DESC)

      context = pyudev.Context()
      monitor = pyudev.Monitor.from_netlink(context)
      monitor.filter_by(subsystem='usb')

      if (isinstance(args.fw_file, str) and len(args.fw_file) > 1):
        fw_data = load_fw_data_from_file(args.fw_file)

        if fw_data != None:
          print("Running...")
          for device in iter(monitor.poll, None):
            if device.action == 'add':
              run(fw_data)
              sleep(2)
      else:
        parser.print_help()

  except KeyboardInterrupt:
    inf = "Closed by user"
    print(f'\n{inf}')
    logger.info(inf)
    sys.exit(0)

###################################################################################################
###################################################################################################

if __name__ == "__main__":
  main()
  