"""Unit Tests for  pitch_handling."""

import unittest

# import * is a bad idea, but we don't want long prefixes al over the place.
import pitch_handling as H


class PitchHandlingTest(unittest.TestCase):

    def setUp(self):
        self.order_id = 1  # easy in base 36
        self.prev_timestamp = 45678
        self.ticker = 'XYZ'
        self.prev_record = H.OrderStateRecord(
            self.order_id, self.prev_timestamp, self.ticker, 10, 5)
        self.orders_state = {self.order_id: self.prev_record}

    def testCanAddIfNoPrevRecord(self):
        # len  8          1   12             1   6        6       10           1
        msg = '11111111' 'A' '000000000007' 'S' '000001' 'XYZxyz' '0000000005' 'Y'
        result = H.handleMessage(self.orders_state, msg)
        self.assertTrue(result.success)
        self.assertEqual(7, result.record.order_id)
        self.assertEqual(11111111, result.record.timestamp)
        self.assertEqual('XYZxyz', result.record.ticker)
        self.assertEqual(1, result.record.amount)
        self.assertEqual(5, result.record.price)
        
        self.assertEqual('XYZxyz', result.ticker)
        self.assertEqual(0, result.value)


    def testCannotAddIfPrevRecordExists(self):
        # len  8          1   12             1   6        6       10           1
        msg = '11111111' 'A' '000000000001' 'S' '000001' 'XYZxyz' '0000000005' 'Y'
        result = H.handleMessage(self.orders_state, msg)
        self.assertFalse(result.success)
        self.assertEqual(self.order_id, result.order_id)
        self.assertEqual('Duplicate Add record', result.message.split(':')[0])

    def testCanPartlyCancelAnOpenOrder(self):
        # len  8          1   12             6     
        msg = '11111111' 'X' '000000000001' '000001'
        result = H.handleMessage(self.orders_state, msg)
        self.assertTrue(result.success)
        self.assertEqual(self.order_id, result.record.order_id)
        self.assertEqual(11111111, result.record.timestamp)
        self.assertEqual(self.prev_record.amount - 1, result.record.amount)
        
    def testCanComplelyCancelAnOpenOrder(self):
        # len  8          1   12             6     
        msg = '11111111' 'X' '000000000001' '000010'
        result = H.handleMessage(self.orders_state, msg)
        self.assertTrue(result.success)
        self.assertEqual(self.order_id, result.record.order_id)
        self.assertEqual(11111111, result.record.timestamp)
        self.assertEqual(0, result.record.amount)
        
    def testCanotCancelMoreThanTheOpenOrderHas(self):
        # len  8          1   12             6     
        msg = '11111111' 'X' '000000000001' '000011'
        result = H.handleMessage(self.orders_state, msg)
        self.assertFalse(result.success)
        self.assertEqual(self.order_id, result.order_id)
        self.assertEqual('Trying to cancel 11 shares when only got 10',
                         result.message.split(':')[0])


if __name__ == '__main__':
    unittest.main()