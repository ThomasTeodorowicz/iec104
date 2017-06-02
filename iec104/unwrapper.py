import struct
import unittest

TESTFR_CON = 131
TESTFR_ACT = 67

STOPDT_CON = 35
STOPDT_ACT = 19

STARTDT_CON = 11
STARTDT_ACT = 7

NO_FUNC = 3

class IEC104Unwrapper():
    """
    This class provides an unwrapper with functions to unwrap IEC 104 messages. Look into the IEC 104 specification to learn the details.
    """

    def unwrap_header(self, header):
        """
        Unwraps a IEC 104 APDU header.
        :param apdu: APDU header as a bytestring.
        :return: Length of the APDU (excluding header). ERROR if failed.
        """
        if not type(header) is bytes:
            return "ERROR: An APDU header has to be a bytestring."
        if len(header) != 2:
        	return "ERROR: An IEC 104 APDU header has to be exactly 2 bytes long."
        start, length = struct.unpack('<2B', header)
        if start != 0x68:
        	return "ERROR: An IEC 104 APDU has to start with a 68H."
        return length

     def unwrap_apdu(self, apdu, length):
        """
        Unwraps a IEC 104 APDU header.
        :param apdu: APDU as a bytestring.
        :param length: Length of the APDU as an integer.
        :return: A tupel containing the information carried by the APDU in the order it was packed(see IEC 104 specification figures). ERROR if failed.
        """
        frame = self.unwrap_frame(struct.unpack('<2H', apdu))
        type_id = struct.unpack('<B', apdu)
        apdu_type = self.unwrap_type_identification(type_id)
        vsq = struct.unpack('<B', apdu)
        msg = self.unwrap_information_objects(type_id, vsq, apdu)
        return frame, apdu_type, vsq, msg

class TestUnwrapper(unittest.TestCase):

    def test_unwrap_header(self):
        unwrapper = IEC104Unwrapper()
        self.assertEqual(26, unwrapper.unwrap_header(b'\x68\x1A'))
        self.assertEqual("ERROR: An APDU header has to be a bytestring.", unwrapper.unwrap_header("Test"))
        self.assertEqual("ERROR: An IEC 104 APDU header has to be exactly 2 bytes long.", unwrapper.unwrap_header(b'\x68\x1A\x11'))
        self.assertEqual("ERROR: An IEC 104 APDU has to start with a 68H.", unwrapper.unwrap_header(b'\x60\x1A'))

    def test_unwrap_apdu(self):
        unwrapper = IEC104Unwrapper()
        self.assertEqual(("i-frame", "M_BO_NA_1", 0, ("periodic", 0, 0), 1, [("Test", (0, 0, 0, 0)), ("Test", (0, 0, 0, 0))], 1, 1)), \
            unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x02\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00')

    def unwrap_frame(self):
        unwrapper = IEC104Unwrapper()
        self.assertEqual(("i-frame", 1, 1)), unwrapper.unwrap_frame(b'\x02\x00\x02\x00')

if __name__ == "__main__":
    unittest.main()