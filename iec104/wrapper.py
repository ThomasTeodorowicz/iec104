import struct
import unittest

TESTFR_CON = 131
TESTFR_ACT = 67

STOPDT_CON = 35
STOPDT_ACT = 19

STARTDT_CON = 11
STARTDT_ACT = 7

NO_FUNC = 3

class IEC104Wrapper():
    """
    This class provides a wrapper with functions to create iec 104 messages and unpack them. Look into the IEC 104 specification to learn the details.
    """

    def __init__(self):
        # Internal counter for the information object address.
        self.information_object_address = 0

    def create_apdu_header(self, apdu):
        """
        Creates a IEC104 APDU header based on the given APDU.
        :param apdu: APDU as bytestring.
        :return: IEC104 APDU header as a bytestring. ERROR if failed.
        """
        if not type(apdu) is bytes:
            return "ERROR: An APDU has to be a bytestring."
        start = b'\x68'
        apdu_length = len(apdu)
        if apdu_length > 253:
            return "ERROR: APDU too long."
        return start + struct.pack("B", len(apdu))

    def create_apdu(self, frame, asdu_type, sequence, cause_of_transmission, common_address, message, ssn = 0, rsn = 0, originator_address = 0):
        """
        Creates a IEC104 APDU without header.
        :param frame: Frame format to be used.
        :param asdu_type: Type of the message as string.
        :param sequence: SQ bit as defined in IEC 104.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N bit and Testbit.
        :param common_address: Common address of ASDUs as integer.
        :param message: Message to be wrapped. Has to be a list containing less than 128 objects/elements.
        :param ssn: Send sequence number. This is also used to store relevant information for the U-Frame(has to contain the function name and type: e.g. "test-con").
        :param rsn: Receive sequence number.
        :param originator_address: Originator address as integer.
        :return: IEC 104 APDU without header as a bytestring. ERROR if failed.
        """
        apci = self.wrap_frame(frame, ssn, rsn)
        if type(apci) is str:
            return apci
        asdu = self.wrap_asdu(asdu_type, sequence, cause_of_transmission, common_address, message, originator_address)
        if type(asdu) is str:
            return asdu
        return apci + asdu

    def wrap_frame(self, frame, ssn, rsn):
        """
        Creates an IEC 104 frame.
        If needed the send sequence number and receive sequence number are used to wrap the frame.
        :param frame: Frame format to be used.
        :param ssn: Send sequence number. This is also used to store relevant information for the U-Frame(has to contain the function name and type: e.g. "test-con").
        :param rsn: Receive sequence number.
        :return: IEC 104 frame as a bytestring. ERROR if failed.
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
        Creates an IEC 104 I-Frame.
        :param ssn: Send sequence number.
        :param rsn: Receive sequence number.
        :return: IEC 104 I-Frame as a bytestring. ERROR if failed.
        """
        if (not type(ssn) is int) or (ssn < 0) or (ssn > 32767):
            return "ERROR: Send sequence number has to be an integer between 0 and 32767."
        if (not type(rsn) is int) or (rsn < 0) or (rsn > 32767):
            return "ERROR: Receive sequence number has to be an integer between 0 and 32767."
        return struct.pack('<1HH', ssn << 1, rsn << 1)

    def s_frame(self, rsn):
        """
        Creates an IEC 104 S-Frame.
        :param rsn: Receive sequence number.
        :return: IEC 104 S-Frame as a bytestring. ERROR if failed.
        """
        if (not type(rsn) is int) or (rsn < 0) or (rsn > 32767):
            return "ERROR: Receive sequence number has to be an integer between 0 and 32767."
        return struct.pack('<2BH', 0x1, 0x00, rsn << 1)

    def u_frame(self, function):
        """
        Creates an IEC 104 U-Frame.
        :param function: Function to be used. Has to contain the function name and type: e.g. "test-con". Defaults to no function being used.
        :return: IEC 104 U-Frame as a bytestring. ERROR if failed.
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
    
    def wrap_asdu(self, asdu_type, sequence, cause_of_transmission, common_address, message, originator_address = 0):
        """
        Creates a IEC 104 ASDU.
        :param asdu_type: Type of the message as string.
        :param sequence: SQ bit as defined in IEC 104.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N bit and Testbit.
        :param common_address: Common address of ASDUs as integer.
        :param message: Message to be wrapped. Has to be a list containing less than 128 objects/elements.
        :param originator_address: Originator address as integer.
        :return: An IEC 104 ASDU as a bytestring. ERROR if failed.
        """
        if not sequence in [0,1]:
            return "ERROR: Sequence bit has to be 0 or 1."
        type_id = self.wrap_asdu_type(asdu_type)
        if type(type_id) is str:
            return type_id
        vsq = self.wrap_variable_structure_qualifier(type_id, sequence, message)
        if type(vsq) is str:
            return vsq
        cot = self.wrap_cause_of_transmission(cause_of_transmission, originator_address)
        if type(cot) is str:
            return cot
        ca = self.wrap_common_address(common_address)
        if type(ca) is str:
            return ca
        io = self.wrap_information_object(type_id, vsq, message)
        if type(io) is str:
            return io
        return struct.pack('<2B', type_id, vsq) + cot + ca + ioa

    def wrap_asdu_type(self, asdu_type):
        """
        Finds the type identification corresponding to the given ASDU type.
        :param asdu_type: Type of the message as string.
        :return: Type identification as integer. ERROR if failed.
        """
        if asdu_type == 'M_BO_NA_1':
            type_id = 7
        elif asdu_type == 'M_ME_NC_1':
            type_id = 13
        elif asdu_type == 'C_SC_NA_1':
            type_id = 45
        elif asdu_type == 'C_IC_NA_1':
            type_id = 100
        elif asdu_type == 'C_RD_NA_1':
            type_id = 102
        else:
            return "ERROR: The ASDU type was not recognized."
        return type_id

    def wrap_variable_structure_qualifier(self, type_id, sequence, message):
        """
        Determines the IEC 104 variable structure qualifier.
        :param type_id: Type of the message as integer.
        :param sequence: SQ bit as defined in IEC 104.
        :param message: Message to be wrapped. Has to be a list containing less than 128 objects/elements.
        :return: Variable structure qualifier as defined in IEC 104 as integer. ERROR if failed.
        """
        if not type(type_id) is int:
             return "ERROR: The type identification has to be an integer."
        if not sequence in [0,1]:
            return "ERROR: Sequence bit has to be 0 or 1."
        if (not type(message) is list) or (len(message) > 127):
             return "ERROR: The message has to be a list containing less than 128 objects/elements."
        if type_id in [7, 13]:
            vsq = len(message)
            if sequence == 1:
                vsq += 128
        elif type_id in [45, 100, 102]:
            vsq = 1
        else:
            return "ERROR: The type identification was not recognized."
        return vsq

    def wrap_cause_of_transmission(self, cause_of_transmission, originator_address = 0):
        """
        Creates an IEC 104 cause of transmission and and IEC 104 originator address.
        :param cause_of_transmission: A tuple containing the cause of transmission as string(e.g. periodic), P/N bit and Testbit.
        :param originator_address: Originator address as integer.
        :return: IEC 104 cause of transmission and IEC 104 originator address as a bytestring. ERROR if failed.
        """
        if not type(cause_of_transmission) is tuple:
            return "ERROR: Cause of transmission also needs a P/N bit and Testbit."
        if not type(cause_of_transmission[0]) is str:
            return "ERROR: Cause of transmission has to be a string."
        if not cause_of_transmission[1] in [0,1]:
            return "ERROR: P/N bit has to be 0 or 1."
        if not cause_of_transmission[2] in [0,1]:
            return "ERROR: Testbit has to be 0 or 1."
        if (not type(originator_address) is int) or (originator_address < 0) or (originator_address > 255):
            return "ERROR: Originator address has to be an integer between 0 and 255."
        if ("periodic" in cause_of_transmission[0]) or ("cyclic" in cause_of_transmission[0]):
            cause = 1
        elif "spontaneous" in cause_of_transmission[0]:
            cause = 3
        elif ("request" in cause_of_transmission[0]) or ("requested" in cause_of_transmission[0]):
            cause = 5
        elif "activation confirmation" in cause_of_transmission[0]:
            cause = 7
        elif "activation" in cause_of_transmission[0]:
            cause = 6
        elif ("return information" in cause_of_transmission[0]) and ("remote command" in cause_of_transmission[0]):
            cause = 11
        else:
            return "ERROR: No cause of transmission was found."
        pn = 64 if cause_of_transmission[1] == 1 else 0
        test = 128 if cause_of_transmission[2] == 1 else 0
        return struct.pack('<2B', cause + pn + test, originator_address)

    def wrap_common_address(self, common_address):
        """
        Creates an IEC 104 common address.
        :param common_address: Common address of ASDUs as integer.
        :return: IEC 104 common address as a bytestring. ERROR if failed.
        """
        if (not type(common_address) is int) or (common_address < 0) or (common_address > 65535):
            return "ERROR: Common address has to be an integer between 0 and 65535."
        return struct.pack('<2B', common_address & 0xFF, (common_address >> 8) & 0xFF)

    def wrap_information_object_address(self):
        """
        Creates an IEC 104 information object address.
        :return: IEC 104 information object address as a bytestring. ERROR if failed.
        """
        if (not type(self.information_object_address) is int) or (self.information_object_address < 0) or (self.information_object_address > 16777215):
            return "ERROR: Information object address has to be an integer between 0 and 16777215."
        return struct.pack('<3B', self.information_object_address & 0xFF, (self.information_object_address >> 8) & 0xFF, (self.information_object_address >> 16) & 0xFF)

    def wrap_information_object(self, type_id, vsq, message):
        """
        Packs the message into the format that is dictated by the type identification.
        :param type_id: Type of the message as integer.
        :param vsq: Variable structure qualifier as defined in IEC 104 as integer.
        :param message: Message to be wrapped. Has to be a list containing less than 128 objects/elements.
        :return: An information object as defined in IEC 104 as a bytestring. ERROR if failed.
        """
        result = b''
        i = 0
        if not type(type_id) is int:
             return "ERROR: The type identification has to be an integer."
        if not type(vsq) is int:
             return "ERROR: The variable structure qualifier has to be an integer."
        if (not type(message) is list) or (len(message) > 127):
             return "ERROR: The message has to be a list containing less than 128 objects/elements."
        # Number of objects/elements expected based on the VSQ value
        length = (vsq & 0x7F)
        if length == 0:
            return result
        if length > len(message):
            return "ERROR: Variable structure qualifier expects more messages than given."
        if length < len(message):
            return "ERROR: Variable structure qualifier expects fewer messages than given."
        # SQ == 1
        if (vsq & 0x80) == 0x80:
            temp = self.wrap_information_object_address()
            if type(temp) is str:
                return temp
            result += temp
            if type_id == 7:
                while i < length:
                    temp = self.wrap_information_object_m_bo_na_1(message[i])
                    if type(temp) is str:
                        return temp
                    result += temp
                    i -= 1
            elif type_id == 13:
                while i < length:
                    temp = self.wrap_information_object_m_me_nc_1(message[i])
                    if type(temp) is str:
                        return temp
                    result += temp
                    i -= 1
            else: 
                return "ERROR: The ASDU type was not recognized or is not fit to be a sequence of elements."
        # SQ == 0
        else:
            if type_id == 7:
                while i < length:
                    temp = self.wrap_information_object_address()
                    if type(temp) is str:
                        return temp
                    result += temp
                    temp = self.wrap_information_object_m_bo_na_1(message[i])
                    if type(temp) is str:
                        return temp
                    result += temp
                    i -= 1
            elif type_id == 13:
                while i < length:
                    temp = self.wrap_information_object_address()
                    if type(temp) is str:
                        return temp
                    result += temp
                    temp = self.wrap_information_object_m_me_nc_1(message[i])
                    if type(temp) is str:
                        return temp
                    result += temp
                    i -= 1
            elif type_id == 45:
                if length != 1:
                    return "ERROR: C_SC_NA_1 length has to be 1."
                temp = self.wrap_information_object_address()
                if type(temp) is str:
                    return temp
                result += temp
                temp = self.wrap_information_object_c_sc_na_1(message)
                if type(temp) is str:
                    return temp
                result += temp
            elif type_id == 100:
                if length != 1:
                    return "ERROR: C_IC_NA_1 length has to be 1."
                temp = self.wrap_information_object_address()
                if type(temp) is str:
                    return temp
                result += temp
                temp = self.wrap_information_object_c_ic_na_1(message)
                if type(temp) is str:
                    return temp
                result += temp
            elif type_id == 102:
                if length != 1:
                    return "ERROR: C_RD_NA_1 length has to be 1."
                temp = self.wrap_information_object_address()
                if type(temp) is str:
                    return temp
                result += temp
            else:
                return "ERROR: The ASDU type was not recognized or is not fit to be a sequence of elements."
        return result

    def wrap_information_object_m_bo_na_1(self, message):
        """
        Packs the message into the M_BO_NA_1 format. 
        :param message: Tuple containing a string and a tuple containing the following bits of the IEC 104 quality descriptor in this order: \
        blocked, substituted, not topical, invalid. 
        :return: Message as a bytestring in the M_BO_NA_1 format. ERROR if failed.
        """
        if not type(message) is tuple:
            return "ERROR: M_BO_NA_1 expects a string and a tuple containing some bits of the IEC 104 quality descriptor in a tupel."
        if not type(message[0]) is str:
             return "ERROR: M_BO_NA_1 expects a string."
        overflow = 1 if len(message[0]) > 32 else 0
        io = self.wrap_quality_descriptor(overflow, message[1][0], message[1][1], message[1][2], message[1][3])
        if type(io) is str:
            return io
        return struct.pack('<4B', message[0]) + io

    def wrap_information_object_m_me_nc_1(self, message):
        """
        Packs the message into the M_ME_NC_1 format.
        :param message: Tuple containing a single float value and a tuple containing the following bits of the quality descriptor in this order: \
        blocked, substituted, not topical, invalid. 
        :return: Message as a bytestring in the M_ME_NC_1 format. ERROR if failed.
        """
        if not type(message) is tuple:
            return "ERROR: M_BO_NA_1 expects a float value and a tuple containing some bits of the IEC 104 quality descriptor in a tupel."
        if not type(message[0]) is float:
             return "ERROR: M_ME_NC_1 expects a float value."
        io = self.wrap_quality_descriptor(0, message[1][0], message[1][1], message[1][2], message[1][3])
        if type(io) is str:
            return io
        return struct.pack('<4B', message[0]) + io

    def wrap_information_object_c_sc_na_1(self, message):
        """
        Packs the message into the C_SC_NA_1 format.
        :param message: Tuple containing a single command state bit and a qualifier of command.
        :return: Message as a bytestring in the C_SC_NA_1 format. ERROR if failed.
        """
        if not type(message) is tuple:
            return "ERROR: C_SC_NA_1 expects a single command state and a qualifier of command in a tupel."
        io = self.wrap_single_command(message[0], message[1])
        return io
        
    def wrap_information_object_c_ic_na_1(self, message):
        """
        Packs the message into the C_IC_NA_1 format.
        :param message: Number representing an interrogation type as defined in IEC 104.
        :return: Message as a bytestring in the C_IC_NA_1 format. ERROR if failed.
        """
        return self.wrap_qualifier_of_interrogation(message)

    def wrap_quality_descriptor(self, overflow, blocked, substituted, not_topical, invalid):
        """
        Creates an IEC 104 quality descriptor.
        :param overflow: Overflow bit as defined in IEC 104.
        :param blocked: Blocked bit as defined in IEC 104.
        :param substituted: Substituted bit as defined in IEC 104.
        :param not_topical: Not topical bit as defined in IEC 104.
        :param invalid: Invalid bit as defined in IEC 104.
        :return: IEC 104 quality descriptor as a bytestring. ERROR if failed.
        """
        if not overflow in [0,1]:
            return "ERROR: Overflow bit has to be 0 or 1."
        if not blocked in [0,1]:
            return "ERROR: Blocked bit has to be 0 or 1."
        if not substituted in [0,1]:
            return "ERROR: Substituted bit has to be 0 or 1."
        if not not_topical in [0,1]:
            return "ERROR: Not topical bit has to be 0 or 1."
        if not invalid in [0,1]:
            return "ERROR: Invalid bit has to be 0 or 1."
        bl = 16 if blocked == 1 else 0
        sb = 32 if substituted == 1 else 0
        nt = 64 if not_topical == 1 else 0
        iv = 128 if invalid == 1 else 0
        return struct.pack('<B', overflow + bl + sb + nt + iv)

    def wrap_single_command(self, single_command_state, qualifier_of_command):
        """
        Creates an IEC 104 quality descriptor.
        :param single_command_state: Single command state bit as defined in IEC 104.
        :param qualifier_of_command: Qualifier of command as defined in IEC 104. S/E is expected as least significant bit.
        :return: Struct containing an IEC 104 quality descriptor as a bytestring. ERROR if failed.
        """
        if not single_command_state in [0,1]:
            return "ERROR: Single command state bit has to be 0 or 1."
        if (not type(qualifier_of_command) is int) or (qualifier_of_command < 0) or (qualifier_of_command > 63):
            return "ERROR: Qualifier of command has to be an integer between 0 and 63."
        qos = self.wrap_qualifier_of_command((qualifier_of_command >> 1) & 0xFF, qualifier_of_command & 0x01)
        qos = (qos << 2) & 0xFF
        return struct.pack('<B', single_command_state + qos)

    def wrap_qualifier_of_command(self, qualifier, select_execute):
        """
        Builds an IEC 104 qualifier of command.
        :param overflow: Number representing a command type as defined in IEC 104.
        :param select_execute: S/E bit as defined in IEC 104.
        :return: An IEC 104 qualifier of command as integer. ERROR if failed.
        """
        if not select_execute in [0,1]:
            return "ERROR: S/E bit has to be 0 or 1."
        if (not type(qualifier) is int) or (qualifier < 0) or (qualifier > 31):
            return "ERROR: Qualifier of command has to be an integer between 0 and 31."
        se = 32 if select_execute == 1 else 0
        return qualifier + se

    def wrap_qualifier_of_interrogation(self, qualifier):
        """
        Creates an IEC 104 qualifier of interrogation.
        :param qualifier: Number representing an interrogation type as defined in IEC 104.
        :return: IEC 104 qualifier of interrogation as a bytestring. ERROR if failed.
        """
        if (not type(qualifier) is int) or (qualifier < 0) or (qualifier > 255):
            return "ERROR: Qualifier of interrogation has to be an integer between 0 and 255."
        return struct.pack('<B', qualifier)

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
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(32768, 1))
        self.assertEqual("ERROR: Send sequence number has to be an integer between 0 and 32767.", wrapper.i_frame("test", 1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, -1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, 3.4))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, 32768))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.i_frame(1, "test"))

    def test_s_frame(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00\x02\x00', wrapper.s_frame(1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(-1))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(3.4))
        self.assertEqual("ERROR: Receive sequence number has to be an integer between 0 and 32767.", wrapper.s_frame(32768))
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
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(7, 0, ["test"]))
        self.assertEqual(2, wrapper.wrap_variable_structure_qualifier(7, 0, ["test", "test"]))
        self.assertEqual(129, wrapper.wrap_variable_structure_qualifier(7, 1, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(13, 0, ["test"]))
        self.assertEqual(2, wrapper.wrap_variable_structure_qualifier(13, 0, ["test", "test"]))
        self.assertEqual(129, wrapper.wrap_variable_structure_qualifier(13, 1, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(45, 0, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(45, 0, ["test", "test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(45, 1, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(100, 0, ["test", "test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(100, 1, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(102, 0, ["test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(102, 0, ["test", "test"]))
        self.assertEqual(1, wrapper.wrap_variable_structure_qualifier(102, 1, ["test"]))
        self.assertEqual("ERROR: The type identification was not recognized.", wrapper.wrap_variable_structure_qualifier(-2, 0, ["test"]))
        self.assertEqual("ERROR: The type identification has to be an integer.", wrapper.wrap_variable_structure_qualifier(3.5, 0, ["test"]))
        self.assertEqual("ERROR: The type identification has to be an integer.", wrapper.wrap_variable_structure_qualifier("test", 0, ["test"]))
        self.assertEqual("ERROR: Sequence bit has to be 0 or 1.", wrapper.wrap_variable_structure_qualifier(7, 20, ["test"]))
        self.assertEqual("ERROR: The message has to be a list containing less than 128 objects/elements.", wrapper.wrap_variable_structure_qualifier(7, 0, "test"))
        self.assertEqual("ERROR: The message has to be a list containing less than 128 objects/elements.", wrapper.wrap_variable_structure_qualifier(7, 0, list("Lorem \
         ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.")))

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
        self.assertEqual("ERROR: Cause of transmission also needs a P/N bit and Testbit.", wrapper.wrap_cause_of_transmission("test", 0))

    def test_p_n(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x41\x00', wrapper.wrap_cause_of_transmission(("periodic", 1, 0), 0))
        self.assertEqual("ERROR: P/N bit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", 54, 0), 0))
        self.assertEqual("ERROR: P/N bit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", 3.4, 0), 0))
        self.assertEqual("ERROR: P/N bit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", "test", 0), 0))

    def test_testbit(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x81\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 1), 0))
        self.assertEqual("ERROR: Testbit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", 0, 54), 0))
        self.assertEqual("ERROR: Testbit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", 0, 3.4), 0))
        self.assertEqual("ERROR: Testbit has to be 0 or 1.", wrapper.wrap_cause_of_transmission(("periodic", 0, "test"), 0))

    def test_original_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x01\x00', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 0))
        self.assertEqual(b'\x01\x0C', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 12))
        self.assertEqual(b'\x01\xFF', wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 255))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), -1))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 3.4))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), 256))
        self.assertEqual("ERROR: Originator address has to be an integer between 0 and 255.", wrapper.wrap_cause_of_transmission(("periodic", 0, 0), "test"))

    def test_common_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x00\x00', wrapper.wrap_common_address(0))
        self.assertEqual(b'\x8B\x13', wrapper.wrap_common_address(5003))
        self.assertEqual(b'\xFF\xFF', wrapper.wrap_common_address(65535))
        self.assertEqual("ERROR: Common address has to be an integer between 0 and 65535.", wrapper.wrap_common_address(-1))
        self.assertEqual("ERROR: Common address has to be an integer between 0 and 65535.", wrapper.wrap_common_address(65536))
        self.assertEqual("ERROR: Common address has to be an integer between 0 and 65535.", wrapper.wrap_common_address(3.4))
        self.assertEqual("ERROR: Common address has to be an integer between 0 and 65535.", wrapper.wrap_common_address("test"))

    def test_information_object_address(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x00\x00\x00', wrapper.wrap_information_object_address())
        wrapper.information_object_address = -1
        self.assertEqual("ERROR: Information object address has to be an integer between 0 and 16777215.", wrapper.wrap_information_object_address())
        wrapper.information_object_address = 16777216
        self.assertEqual("ERROR: Information object address has to be an integer between 0 and 16777215.", wrapper.wrap_information_object_address())
        wrapper.information_object_address = 3.4
        self.assertEqual("ERROR: Information object address has to be an integer between 0 and 16777215.", wrapper.wrap_information_object_address())
        wrapper.information_object_address = "test"
        self.assertEqual("ERROR: Information object address has to be an integer between 0 and 16777215.", wrapper.wrap_information_object_address())

    def test_quality_descriptor(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x00', wrapper.wrap_quality_descriptor(0, 0, 0, 0, 0))
        self.assertEqual(b'\x01', wrapper.wrap_quality_descriptor(1, 0, 0, 0, 0))
        self.assertEqual(b'\x10', wrapper.wrap_quality_descriptor(0, 1, 0, 0, 0))
        self.assertEqual(b'\x20', wrapper.wrap_quality_descriptor(0, 0, 1, 0, 0))
        self.assertEqual(b'\x40', wrapper.wrap_quality_descriptor(0, 0, 0, 1, 0))
        self.assertEqual(b'\x80', wrapper.wrap_quality_descriptor(0, 0, 0, 0, 1))
        self.assertEqual(b'\xF1', wrapper.wrap_quality_descriptor(1, 1, 1, 1, 1))
        self.assertEqual("ERROR: Overflow bit has to be 0 or 1.", wrapper.wrap_quality_descriptor(10, 0, 0, 0, 0))
        self.assertEqual("ERROR: Blocked bit has to be 0 or 1.", wrapper.wrap_quality_descriptor(0, 10, 0, 0, 0))
        self.assertEqual("ERROR: Substituted bit has to be 0 or 1.", wrapper.wrap_quality_descriptor(0, 0, 10, 0, 0))
        self.assertEqual("ERROR: Not topical bit has to be 0 or 1.", wrapper.wrap_quality_descriptor(0, 0, 0, 10, 0))
        self.assertEqual("ERROR: Invalid bit has to be 0 or 1.", wrapper.wrap_quality_descriptor(0, 0, 0, 0, 10))

    def test_qualifier_of_interrogation(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\xFF', wrapper.wrap_qualifier_of_interrogation(255))
        self.assertEqual("ERROR: Qualifier of interrogation has to be an integer between 0 and 255.", wrapper.wrap_qualifier_of_interrogation(-1))
        self.assertEqual("ERROR: Qualifier of interrogation has to be an integer between 0 and 255.", wrapper.wrap_qualifier_of_interrogation(3.4))
        self.assertEqual("ERROR: Qualifier of interrogation has to be an integer between 0 and 255.", wrapper.wrap_qualifier_of_interrogation("test"))
        self.assertEqual("ERROR: Qualifier of interrogation has to be an integer between 0 and 255.", wrapper.wrap_qualifier_of_interrogation(256))

    def test_qualifier_of_command(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(0, wrapper.wrap_qualifier_of_command(0, 0))
        self.assertEqual(31, wrapper.wrap_qualifier_of_command(31, 0))
        self.assertEqual(32, wrapper.wrap_qualifier_of_command(0, 1))
        self.assertEqual("ERROR: S/E bit has to be 0 or 1.", wrapper.wrap_qualifier_of_command(0, 10))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 31.", wrapper.wrap_qualifier_of_command(-1, 0))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 31.", wrapper.wrap_qualifier_of_command(3.4, 0))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 31.", wrapper.wrap_qualifier_of_command("test", 0))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 31.", wrapper.wrap_qualifier_of_command(32, 0))

    def test_single_command(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x00', wrapper.wrap_single_command(0, 0))
        self.assertEqual(b'\x01', wrapper.wrap_single_command(1, 0))
        self.assertEqual(b'\xFC', wrapper.wrap_single_command(0, 63))
        self.assertEqual("ERROR: Single command state bit has to be 0 or 1.", wrapper.wrap_single_command(10, 0))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 63.", wrapper.wrap_single_command(0, -1))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 63.", wrapper.wrap_single_command(0, 3.4))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 63.", wrapper.wrap_single_command(0, "test"))
        self.assertEqual("ERROR: Qualifier of command has to be an integer between 0 and 63.", wrapper.wrap_single_command(0, 64))

    def test_asdu(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x07\x01\x01\x00\x01\x00\x00\x00\x00', wrapper.wrap_asdu("M_BO_NA_1", 0, ("periodic", 0, 0), 1, ["test"], 0))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.wrap_asdu(1, 0, ("periodic", 0, 0), 1, ["test"], 0))
        self.assertEqual("ERROR: No cause of transmission was found.", wrapper.wrap_asdu("M_BO_NA_1", 0, ("test", 0, 0), 1, ["test"], 0))
        self.assertEqual("ERROR: Common address has to be an integer between 0 and 65535.", wrapper.wrap_asdu("M_BO_NA_1", 0, ("periodic", 0, 0), -1, ["test"], 0))
        wrapper.information_object_address = -1
        self.assertEqual("ERROR: Information object address has to be an integer between 0 and 16777215.", wrapper.wrap_asdu("M_BO_NA_1", 0, ("periodic", 0, 0), 1, ["test"], 0))

    def test_create_apdu(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x02\x00\x02\x00\x07\x01\x01\x00\x01\x00\x00\x00\x00', wrapper.create_apdu("i-frame", "M_BO_NA_1", 0, ("periodic", 0, 0), 1, ["test"], 1, 1))
        self.assertEqual("ERROR: No valid frame format was given.", wrapper.create_apdu("test", "M_BO_NA_1", 0, ("periodic", 0, 0), 1, ["test"], 1, 1))
        self.assertEqual("ERROR: The ASDU type was not recognized.", wrapper.create_apdu("i-frame", "test", 0, ("periodic", 0, 0), 1, ["test"], 1, 1))

    def test_create_header(self):
        wrapper = IEC104Wrapper()
        self.assertEqual(b'\x68\x0d', wrapper.create_apdu_header(b'\x02\x00\x02\x00\x07\x01\x01\x00\x01\x00\x00\x00\x00'))
        self.assertEqual("ERROR: APDU too long.", wrapper.create_apdu_header("Lorem ipsum dolor sit amet, consetetur sadipscing elitr, \
            sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et \
            justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimat".encode()))
        self.assertEqual("ERROR: An APDU has to be a bytestring.", wrapper.create_apdu_header("test"))

if __name__ == "__main__":
    unittest.main()