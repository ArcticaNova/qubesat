import sys
import unittest
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, './drivers/emulation/lib')
sys.path.insert(0, './drivers/emulation/')
sys.path.insert(0, './applications/flight')
sys.path.insert(0, './applications/flight/lib')
sys.path.insert(0, './frame/')

import Tasks.radio as radio
import radio_utils.commands as cdh
from state_machine import state_machine
from testutils import send_cmd
from radio_utils import transmission_queue as tq
from radio_utils import message
from pycubed import cubesat
import settings
from radio_test_utils import init_radio_task_for_testing
Message = message.Message

settings.TX_ALLLOWED = True
state_machine.state = 'Debug'

cubesat.radio._rx_time_bias = 0.0
cubesat.radio._rx_time_dev = 0.0

class CommandTests(IsolatedAsyncioTestCase):

    async def test_query(self):
        rt = init_radio_task_for_testing()

        await self.cmd_test(rt, cdh.QUERY, b'5+5', b'10')
        await self.cmd_test(rt, cdh.QUERY, b'12*12', b'144')

    async def test_tq_len(self):
        rt = init_radio_task_for_testing()

        await self.cmd_test(rt, cdh.TQ_SIZE, b'', b'0')

    async def test_tq_clear(self):
        rt = init_radio_task_for_testing()

        # clog tx queue
        send_cmd(cdh.EXEC_PY, b"for _ in range(40):\n\ttq.push(Message(5, b'hello'))")
        await rt.main_task()

        # clear the tx queue
        for _ in range(radio.TX_SKIP):
            send_cmd(cdh.CLEAR_TX_QUEUE, b'')
            await rt.main_task()
            await rt.main_task()

        await self.cmd_test(rt, cdh.TQ_SIZE, b'', b'0')

    async def cmd_test(self, rt, cmd, args, expected):
        """Test that RX of a command with and without args works"""
        tq.clear()

        send_cmd(cmd, args)
        for _ in range(5):
            await rt.main_task()

        last_tx_packet = cubesat.radio.test.last_tx_packet
        self.assertIsNotNone(last_tx_packet, "No packet was sent")
        self.assertEqual(last_tx_packet[1:], expected)


if __name__ == '__main__':
    unittest.main()
