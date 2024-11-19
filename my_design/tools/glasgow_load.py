import argparse
import asyncio
import usb1

from glasgow.device import GlasgowDeviceError
from glasgow.device.hardware import GlasgowHardwareDevice, REQ_FPGA_CFG, REQ_BITSTREAM_ID


async def download_bitstream(self, bitstream, bitstream_id=b"\xff" * 16):
        # Send consecutive chunks of bitstream. Sending 0th chunk also clears the FPGA bitstream.
        index = 0
        while index * 1024 < len(bitstream):
            await self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_FPGA_CFG,
                                     0, index, bitstream[index * 1024:(index + 1) * 1024])
            index += 1
        # Complete configuration by setting bitstream ID. This starts the FPGA.
        try:
            await self.control_write(usb1.REQUEST_TYPE_VENDOR, REQ_BITSTREAM_ID,
                                     0, 0, bitstream_id)
        except usb1.USBErrorPipe:
            raise GlasgowDeviceError("FPGA configuration failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bitstream", type=argparse.FileType("rb"))
    args = parser.parse_args()

    async def do_program():
        device = GlasgowHardwareDevice()
        await download_bitstream(device, args.bitstream.read())
        await device.set_voltage("AB", 3.3)
        device.close()

    asyncio.run(do_program())


if __name__ == "__main__":
    main()
