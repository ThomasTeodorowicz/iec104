import struct
import unittest
# This class provides a wrapper with functions to create iec 104 messages and unpack them. Look into the IEC 104 specification to learn the details.

TESTFR_CON = 131
TESTFR_ACT = 67

STOPDT_CON = 35
STOPDT_ACT = 19

STARTDT_CON = 11
STARTDT_ACT = 7

NO_FUNC = 3

class IEC104Wrapper():

    def create_apdu_header(self, apdu):
        """
        Creates a IEC104 APDU header based on the given APDU.
        :param apdu: APDU as bytestring.
        :return: A struct containing an IEC104 APDU header as bytestring. ERROR if failed.
        """
        if not type(apdu) is bytes:
            return "ERROR: An APDU has to be a bytestring."
        start = b'\x68'
        apdu_length = len(apdu)
        if apdu_length > 253:
            return "ERROR: APDU too long."
        return start + struct.pack("B", len(apdu))

    def create_apdu(self, frame, asdu_type, cause_of_transmission, originator_address, common_address, information_object_address, message, ssn = 0, rsn = 0):
        """
        Creates a IEC104 APDU without header.
        :param frame: Frame format to be used.
        :param asdu_type: Type of the message as string.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N Bit(defaults to 0) and Testbit(defaults to 0).
        :param originator_address: Originator address as integer.
        :param common_address: Common address of ASDUs as integer.
        :param information_object_address: Information object address as integer.
        :param message: Message to be wrapped.
        :param ssn: Send sequence number. This is also used to store relevant information for the U-Frame(has to contain the function name and type: e.g. "test-con").
        :param rsn: Receive sequence number.
        :return: Struct containing an IEC 104 APDU without header as bytestring. ERROR if failed.
        """
        apci = self.wrap_frame(frame, ssn, rsn)
        if type(apci) is str:
            return apci
        asdu = self.wrap_asdu(asdu_type, cause_of_transmission, originator_address, common_address, information_object_address, message)
        if type(asdu) is str:
            return asdu
        return apci + asdu

    def wrap_frame(self, frame, ssn, rsn):
        """
        Returns a struct containing a IEC 104 frame based on the given frame format.
        If needed the send sequence number and receive sequence number are used to wrap the frame.
        :param frame: Frame format to be used.
        :param ssn: Send sequence number. This is also used to store relevant information for the U-Frame(has to contain the function name and type: e.g. "test-con").
        :param rsn: Receive sequence number.
        :return: Struct containing an IEC 104 frame as bytestring. ERROR if failed.
        """
        if frame == "i-frame":
            res = self.i_frame(ssn, rsn)
        elif frame == "s-frame":
            res = self.s_frame(rsn)
        elif frame == "u-frame":
            res = self.u_frame(ssn)
        else:
            res = "ERROR: No valid frame format was given."
        return res

    def i_frame(self, ssn, rsn):
        """
        Creates struct containing a IEC 104 I-Frame based on the given send sequence number and receive sequence number.
        :param ssn: Send sequence number.
        :param rsn: Receive sequence number.
        :return: Struct containing an IEC 104 I-Frame as bytestring. ERROR if failed.
        """
        if (not type(ssn) is int) or (ssn < 0) or (ssn > 32767):
            return "ERROR: Send sequence number has to be an integer between 0 and 32767."
        if (not type(rsn) is int) or (rsn < 0) or (rsn > 32767):
            return "ERROR: Receive sequence number has to be an integer between 0 and 32767."
        return struct.pack('<1HH', ssn << 1, rsn << 1)

    def s_frame(self, rsn):
        """
        Creates struct containing a IEC 104 S-Frame based on the given receive sequence number.
        :param rsn: Receive sequence number.
        :return: Struct containing an IEC 104 S-Frame as bytestring. ERROR if failed.
        """
        if (not type(rsn) is int) or (rsn < 0) or (rsn > 32767):
            return "ERROR: Receive sequence number has to be an integer between 0 and 32767."
        return struct.pack('<2BH', 0x1, 0x00, rsn << 1)

    def u_frame(self, function):
        """
        Creates struct containing a IEC 104 U-Frame based on the given information.
        :param function: Function to be used. Has to contain the function name and type: e.g. "test-con". Defaults to no function being used.
        :return: Struct containing an IEC 104 U-Frame as bytestring. ERROR if failed.
        """
        byte = NO_FUNC
        function = function.lower()
        if "con" in function:
            if "test" in function:
                byte = TESTFR_CON
            if "stop" in function:
                byte = STOPDT_CON
            if "start" in function:
                byte = STARTDT_CON
        if "act" in function:
            if "test" in function:
                byte = TESTFR_ACT
            if "stop" in function:
                byte = STOPDT_ACT
            if "start" in function:
                byte = STARTDT_ACT
        if byte == NO_FUNC:
            print("Warning: U-Frame was made without an active function.")
        return struct.pack('<2BH', byte, 0x00, 0x00)
    
    def wrap_asdu(self, asdu_type, cause_of_transmission, originator_address, common_address, information_object_address, message):
        """
        Adds a IEC 104 ASDU to a struct.
        :param asdu_type: Type of the message as string.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N Bit(defaults to 0) and Testbit(defaults to 0).
        :param originator_address: Originator address as integer.
        :param common_address: Common address of ASDUs as integer.
        :param information_object_address: Information object address as integer.
        :param message: Message to be wrapped.
        :return: Struct containing an IEC 104 ASDU as bytestring. ERROR if failed.
        """
        type_id = self.wrap_asdu_type(asdu_type)
        if type(type_id) is str:
            return type_id
        vsq = self.wrap_variable_structure_qualifier(type_id)
        if type(vsq) is str:
            return type_id
        cot = self.wrap_cause_of_transmission(cause_of_transmission, originator_address)
        if type(cot) is str:
            return cot
        ca = self.wrap_common_address(common_address)
        if type(ca) is str:
            return ca
        ioa = self.wrap_information_object_address(information_object_address)
        if type(ioa) is str:
            return ioa
        return struct.pack('<B', type_id) + vsq + cot + ca + ioa

    def wrap_asdu_type(self, asdu_type):
        """
        Finds the type identification corresponding to the given ASDU type.
        :param asdu_type: Type of the message as string.
        :return: Type identification as integer. ERROR if failed.
        """
        type_id = "ERROR: The ASDU type was not recognized."
        if asdu_type == 'M_BO_NA_1':
            type_id = 7
        if asdu_type == 'M_ME_NC_1':
            type_id = 13
        if asdu_type == 'C_SC_NA_1':
            type_id = 45
        if asdu_type == 'C_IC_NA_1':
            type_id = 100
        if asdu_type == 'C_RD_NA_1':
            type_id = 102
        return type_id

    def wrap_variable_structure_qualifier(self, type_id):
        """
        Adds a IEC 104 variable structure qualifier to a struct based on the type identification.
        :param type_id: Type of the message as integer.
        :return: Struct containing an IEC 104 variable structure qualifier as bytestring. ERROR if failed.
        """
        vsq = "ERROR: The type identification was not recognized."
        if type_id in [7, 13]:
            # TODO In this case this should actually be variable.
            vsq = 1
        if type_id in [45, 100, 102]:
            vsq = 1
        if type(vsq) is str:
             return vsq
        return struct.pack('<B', vsq)

    def wrap_cause_of_transmission(self, cause_of_transmission, originator_address):
        """
        Adds a IEC 104 cause of transmission and originator address to a struct based on the type identification.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N Bit(defaults to 0) and Testbit(defaults to 0).
        :param originator_address: Originator address as integer.
        :return: Struct containing an IEC 104 cause of transmission and originator address as bytestring. ERROR if failed.
        """
        cause = "ERROR: No cause of transmission was found."
        pn = 0
        test = 0
        if not type(cause_of_transmission[0]) is str:
            return "ERROR: Cause of transmission has to be a string."
        if ("periodic" in cause_of_transmission[0]) or ("cyclic" in cause_of_transmission[0]):
            cause = 1
        if "spontaneous" in cause_of_transmission[0]:
            cause = 3
        if ("request" in cause_of_transmission[0]) or ("requested" in cause_of_transmission[0]):
            cause = 5
        if "activation" in cause_of_transmission[0]:
            cause = 6
        if "activation confirmation" in cause_of_transmission[0]:
            cause = 7
        if ("return information" in cause_of_transmission[0]) and ("remote command" in cause_of_transmission[0]):
            cause = 11
        if type(cause) is str:
            return cause
        if cause_of_transmission[1] == 1:
            pn = 64
        if cause_of_transmission[2] == 1:
            test = 128
        if (not type(originator_address) is int) or (originator_address < 0) or (originator_address > 255):
            return "ERROR: Originator address has to be an integer between 0 and 255."
        return struct.pack('<2B', cause + pn + test, originator_address)

    def wrap_common_address(self, common_address):
        """
        Adds a IEC 104 common address to a struct.
        :param common_address: Common address of ASDUs as integer.
        :param message: Message to be wrapped.
        :return: Struct containing an IEC 104 common address as bytestring. ERROR if failed.
        """
        if (not type(common_address) is int) or (common_address < 1) or (common_address > 65535):
            return "ERROR: Common address has to be an integer between 1 and 65535."
        return struct.pack('<2B', common_address & 0xFF, (common_address >> 8) & 0xFF)

    def wrap_information_object_address(self, information_object_address):
        """
        Adds a IEC 104 information object address to a struct.
        :param information_object_address: Information object address as integer.
        :return: Struct containing an IEC 104 information object address as bytestring. ERROR if failed.
        """
        if (not type(information_object_address) is int) or (information_object_address < 0) or (information_object_address > 16777215):
            return "ERROR: Information object address has to be an integer between 1 and 16777215."
        return struct.pack('<3B', information_object_address & 0xFF, (information_object_address >> 8) & 0xFF, (information_object_address >> 16) & 0xFF)


    def unwrap_message(self):
        pass

class TestWrapper(unittest.TestCase):

    def test_wrap_frame(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x02\x00\x02\x00', wrapper.wrap_frame("i-frame", 1, 1))
        self.assertEqual(b'\x01\x00\x02\x00', wrapper.wrap_frame("s-frame", 0, 1))
        self.assertEqual(b'\x83\x00\x00\x00', wrapper.wrap_frame("u-frame", "testcon", 0))
        self.assertEqual("ERROR: No valid frame format was given.", wrapper.wrap_frame("test", 0, 0))

    def test_i_frame(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x02\x00\x02\x00', wrapper.i_frame(1, 1))
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(-1, 1))
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(3.4, 1))
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(255643456234, 1))
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame("test", 1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, -1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, 3.4))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, 255643456234))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, "test"))

    def test_s_frame(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00\x02\x00', wrapper.s_frame(1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(-1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(3.4))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(255643456234))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame("test"))

    def test_u_frame(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x83\x00\x00\x00', wrapper.u_frame("testcon"))
        self.assertEqual(b'\x0b\x00\x00\x00', wrapper.u_frame("startcon"))
        self.assertEqual(b'\x23\x00\x00\x00', wrapper.u_frame("stopcon"))
        self.assertEqual(b'\x43\x00\x00\x00', wrapper.u_frame("testact"))
        self.assertEqual(b'\x07\x00\x00\x00', wrapper.u_frame("startact"))
        self.assertEqual(b'\x13\x00\x00\x00', wrapper.u_frame("stopact"))
        self.assertEqual(b'\x03\x00\x00\x00', wrapper.u_frame("test"))


    def test_variable_structure_qualifier(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01', wrapper.wrap_variable_structure_qualifier(7))
        self.assertEqual(b'\x01', wrapper.wrap_variable_structure_qualifier(13))
        self.assertEqual(b'\x01', wrapper.wrap_variable_structure_qualifier(45))
        self.assertEqual(b'\x01', wrapper.wrap_variable_structure_qualifier(100))
        self.assertEqual(b'\x01', wrapper.wrap_variable_structure_qualifier(102))
        self.assertEqual("ERROR: The type identification was not recognized.", wrapper.wrap_variable_structure_qualifier(-2))
        self.assertEqual("ERROR: The type identification was not recognized.", wrapper.wrap_variable_structure_qualifier(3.5))
        self.assertEqual("ERROR: The type identification was not recognized.", wrapper.wrap_variable_structure_qualifier("test"))

    def test_asdu_type(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(7, wrapper.wrap_asdu_type("M_BO_NA_1"))
        self.assertEqual(13, wrapper.wrap_asdu_type("M_ME_NC_1"))
        self.assertEqual(45, wrapper.wrap_asdu_type("C_SC_NA_1"))
        self.assertEqual(100, wrapper.wrap_asdu_type("C_IC_NA_1"))
        self.assertEqual(102, wrapper.wrap_asdu_type("C_RD_NA_1"))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.wrap_asdu_type("test"))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.wrap_asdu_type(1))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.wrap_asdu_type(3.4))

    def test_cause_of_transmission(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("cyclic", 0, 0), 0))
        self.assertEqual(b'\x03\x00', wrapper.wrap_cause_of_transmission(("spontaneous", 0, 0), 0))
        self.assertEqual(b'\x05\x00', wrapper.wrap_cause_of_transmission(("request", 0, 0), 0))
        self.assertEqual(b'\x05\x00', wrapper.wrap_cause_of_transmission(("requested", 0, 0), 0))
        self.assertEqual(b'\x06\x00', wrapper.wrap_cause_of_transmission(("activation", 0, 0), 0))
        self.assertEqual(b'\x07\x00', wrapper.wrap_cause_of_transmission(("activation confirmation", 0, 0), 0))
        self.assertEqual(b'\x0b\x00', wrapper.wrap_cause_of_transmission(("return information due to remote command", 0, 0), 0))
        self.assertEqual("ERROR: No cause of transmission was found.", wrapper.wrap_cause_of_transmission(("test", 0, 0), 0))
        self.assertEqual("ERROR: Cause of transmission has to be a string.", wrapper.wrap_cause_of_transmission((0, 0, 0), 0))

    def test_p_n(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 54, 0), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 3.4, 0), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", "test", 0), 0))
        self.assertEqual(b'\x41\x00', wrapper.wrap_cause_of_transmission(("periodic", 1, 0), 0))

    def test_testbit(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 54), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 3.4), 0))
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, "test"), 0))
        self.assertEqual(b'\x81\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 1), 0))

    def test_original_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x01\x0C', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 12))
        self.assertEqual(b'\x01\xFF', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 255))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), -1))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 3.4))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 2556))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), "test"))

    def test_common_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_common_address(1))
        self.assertEqual(b'\x8B\x13', wrapper.wrap_common_address(5003))
        self.assertEqual(b'\xFF\xFF', wrapper.wrap_common_address(65535))
        self.assertEqual("ERROR: Common address has to be an integer between 1 and 65535.", wrapper.wrap_common_address(0))
        self.assertEqual("ERROR: Common address has to be an integer between 1 and 65535.", wrapper.wrap_common_address(44444444443))
        self.assertEqual("ERROR: Common address has to be an integer between 1 and 65535.", wrapper.wrap_common_address(3.4))
        self.assertEqual("ERROR: Common address has to be an integer between 1 and 65535.", wrapper.wrap_common_address("test"))

    def test_information_object_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x00\x00\x00', wrapper.wrap_information_object_address(0))
        self.assertEqual(b'\x8b\x13\x00', wrapper.wrap_information_object_address(5003))
        self.assertEqual(b'\xFF\xFF\xFF', wrapper.wrap_information_object_address(16777215))
        self.assertEqual("ERROR: Information object address has to be an integer between 1 and 16777215.", wrapper.wrap_information_object_address(-1))
        self.assertEqual("ERROR: Information object address has to be an integer between 1 and 16777215.", wrapper.wrap_information_object_address(44444444443))
        self.assertEqual("ERROR: Information object address has to be an integer between 1 and 16777215.", wrapper.wrap_information_object_address(3.4))
        self.assertEqual("ERROR: Information object address has to be an integer between 1 and 16777215.", wrapper.wrap_information_object_address("test"))

    def test_asdu(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x07\x01\x01\x00\x01\x00\x00\x00\x00', wrapper.wrap_asdu("M_BO_NA_1", ("periodic", 0, 0), 0, 1, 0, "test"))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.wrap_asdu(1, ("periodic", 0, 0), 0, 1, 0, "test"))
        self.assertEqual("ERROR: No cause of transmission was found.", wrapper.wrap_asdu("M_BO_NA_1", ("test", 0, 0), 0, 1, 0, "test"))
        self.assertEqual("ERROR: Common address has to be an integer between 1 and 65535.", wrapper.wrap_asdu("M_BO_NA_1", ("periodic", 0, 0), 0, -1, 0, "test"))
        self.assertEqual("ERROR: Information object address has to be an integer between 1 and 16777215.", wrapper.wrap_asdu("M_BO_NA_1", ("periodic", 0, 0), 0, 1, -1, "test"))

    def test_create_apdu(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x02\x00\x02\x00\x07\x01\x01\x00\x01\x00\x00\x00\x00', wrapper.create_apdu("i-frame", "M_BO_NA_1", ("periodic", 0, 0), 0, 1, 0, "test", 1, 1))
        self.assertEqual("ERROR: No valid frame format was given.", wrapper.create_apdu("test", "M_BO_NA_1", ("periodic", 0, 0), 0, 1, 0, "test", 1, 1))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.create_apdu("i-frame", "test", ("periodic", 0, 0), 0, 1, 0, "test", 1, 1))

    def test_create_header(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x68\x0d', wrapper.create_apdu_header(b'\x02\x00\x02\x00\x07\x01\x01\x00\x01\x00\x00\x00\x00'))
        self.assertEqual("ERROR: APDU too long.", wrapper.create_apdu_header("Lorem ipsum dolor sit amet, consetetur sadipscing elitr, \
            sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et \
            justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimat".encode()))
        self.assertEqual("ERROR: An APDU has to be a bytestring.", wrapper.create_apdu_header("test"))

if __name__ == "__main__":
    unittest.main()