import struct
import unittest

TESTFR_CON = 131
TESTFR_ACT = 67

STOPDT_CON = 35
STOPDT_ACT = 19

STARTDT_CON = 11
STARTDT_ACT = 7

NO_FUNC = 3

M_BO_NA_1 = 7
M_ME_NC_1 = 13
C_SC_NA_1 = 45
C_IC_NA_1 = 100
C_RD_NA_1 = 102

PERIODIC = 1
SPONTANEOUS = 3
REQUEST_REQUESTED = 5
ACTIVATION = 6
ACTIVATION_CONFIRMATION = 7
RETURN_INFORMATION_BY_REMOTE_COMMAND = 11

INFORMATION_OBJECT_ADDRESS_LENGTH = 3
M_BO_NA_1_LENGTH = 5
M_ME_NC_1_LENGTH = 5

APDU_MIN_LEN = 10

class IEC104Unwrapper():
    """
    This class provides an unwrapper with functions to unwrap IEC 104 messages. Look into the IEC 104 specification to learn the details.
    """

    def unwrap_header(self, header):
        """
        Unwraps an IEC 104 APDU header.
        :param apdu: APDU header as a bytestring.
        :return: Length of the APDU (excluding header). ERROR if failed.
        """
        if not type(header) is bytes:
            return "ERROR: The APDU header has to be a bytestring."
        if len(header) != 2:
            return "ERROR: The APDU header has to be exactly 2 bytes long."
        start, length = struct.unpack('<2B', header)
        if start != 0x68:
            return "ERROR: The APDU has to start with a 68H."
        return length

    def unwrap_apdu(self, apdu, length):
        """
        Unwraps an IEC 104 APDU header.
        :param apdu: APDU as a bytestring.
        :param length: Length of the APDU as an integer.
        :return: A tuple containing the information carried by the APDU in the order it was packed(see IEC 104 specification figures). ERROR if failed.
        """
        offset = 0
        if not type(apdu) is bytes:
            return "ERROR: The APDU has to be a bytestring."
        if (not type(length) is int) or (length < APDU_MIN_LEN):
            return "ERROR: The length has to be an integer bigger than " + str(APDU_MIN_LEN - 1) + "(excluding header)."
        frame = self.unwrap_frame(struct.unpack_from('<4B', apdu, offset))
        if type(frame) is str:
            return frame
        type_id = struct.unpack_from('<B', apdu, offset + 4)[0]
        asdu_type = self.unwrap_type_identification(type_id)
        if "ERROR:" in asdu_type:
            return asdu_type
        vsq = self.unwrap_variable_structure_qualifier(struct.unpack_from('<B', apdu, offset + 5)[0])
        if type(vsq) is str:
            # At the moment this is not reachable due to the APDU being checked to be a bytestring. 
            # In case it becomes possible in the future the check is already here but a test has yet to be added.
            return vsq
        cot = self.unwrap_cause_of_transmission(struct.unpack_from('<B', apdu, offset + 6)[0])
        if type(cot) is str:
            return cot
        oa = struct.unpack_from('<B', apdu, offset + 7)[0]
        ca = struct.unpack_from('<2B', apdu, offset + 8)[0]
        if vsq[1] == 0:
            if (len(apdu) - APDU_MIN_LEN) != 0:
                return "ERROR: No information object was expected but the APDU still contains information."
            else:
                return (frame, asdu_type, (vsq[0], vsq[1]), cot, oa, ca, "No information objects/elements.")
        io = self.unwrap_information_objects(type_id, vsq[0], vsq[1], apdu, (length - APDU_MIN_LEN), offset + 10)
        if type(io) is str:
            return io
        return (frame, asdu_type, (vsq[0], vsq[1]), cot, oa, ca, io)

    def unwrap_frame(self, frame):
        """
        Unwraps an IEC 104 frame.
        :param frame: Tuple containing 4 integers representing a frame.
        :return: A tuple containing the frame type and depending on the type some of the following: send sequence number, receive sequence number, function name. ERROR if failed.
        """
        if (not type(frame) is tuple) or (len(frame) != 4):
            return "ERROR: The frame has to be a tuple containing 4 integers."
        if (frame[0] & 0x01) == 0:
            frame_type = "i-frame"
            ssn = (frame[1] << 7) + (frame[0] >> 1)
            rsn = (frame[3] << 7) + (frame[2] >> 1)
        else:
            if frame[0] == 1:
                frame_type = "s-frame"
                ssn = 1
                rsn = (frame[3] << 7) + (frame[2] >> 1)
            else:
                if (frame[0] & 0x03) == 3:
                    frame_type = "u-frame"
                    if frame[0] == TESTFR_CON:
                        ssn = "TESTFR_CON"
                    elif frame[0] == TESTFR_ACT:
                        ssn = "TESTFR_ACT"
                    elif frame[0] == STOPDT_CON:
                        ssn = "STOPDT_CON"
                    elif frame[0] == STOPDT_ACT:
                        ssn = "STOPDT_ACT"
                    elif frame[0] == STARTDT_CON:
                        ssn = "STARTDT_CON"
                    elif frame[0] == STARTDT_ACT:
                        ssn = "STARTDT_ACT"
                    elif frame[0] == NO_FUNC:
                        ssn = "NO_FUNC"
                    else:
                        return "ERROR: Function type could not be determined."
                    rsn = 0
                else:
                    return "ERROR: Frame type could not be determined."
        return (frame_type, ssn, rsn)
    
    def unwrap_type_identification(self, type_id):
        """
        Finds the IEC 104 ASDU type corresponding to the given type identification.
        :param type_id: Type identification as integer.
        :return: ASDU Type as string. ERROR if failed.
        """
        if not type(type_id) is int:
            return "ERROR: The type identification has to be an integer."
        if type_id == M_BO_NA_1:
            asdu_type = "M_BO_NA_1"
        elif type_id == M_ME_NC_1:
            asdu_type = "M_ME_NC_1"
        elif type_id == C_SC_NA_1:
            asdu_type = "C_SC_NA_1"
        elif type_id == C_IC_NA_1:
            asdu_type = "C_IC_NA_1"
        elif type_id == C_RD_NA_1:
            asdu_type = "C_RD_NA_1"
        else:
            return "ERROR: The ASDU type was not recognized."
        return asdu_type

    def unwrap_variable_structure_qualifier(self, vsq):
        """
        Reads the sequence bit and length from an IEC 104 variable structure qualifier.
        :param vsq: Variable structure qualifier as integer.
        :return: Tuple containing the sequence bit and the length. ERROR if failed.
        """
        if not type(vsq) is int:
            return "ERROR: The variable structure qualifier has to be an integer."
        return (((vsq >> 7) & 0x01), (vsq & 0x7F))

    def unwrap_cause_of_transmission(self, cot):
        """
        Reads the P/N bit, the Testbit and cause of transmission from an integer.
        :param cot: Integer representing a cause of transmission and the corresponding P/N bit and Testbit.
        :return: Tuple containing the cause of transmission, the P/N bit and the Testbit. ERROR if failed.
        """
        if not type(cot) is int:
            return "ERROR: The cause of transmission, P/N bit and Testit have to be wrapped into an integer."
        cause_id = (cot & 0x3F)
        if cause_id == PERIODIC:
            cause = "periodic"
        elif cause_id == SPONTANEOUS:
            cause = "spontaneous"
        elif cause_id == REQUEST_REQUESTED:
            cause = "request or requested"
        elif cause_id == ACTIVATION:
            cause = "activation"
        elif cause_id == ACTIVATION_CONFIRMATION:
            cause = "activation confirmation"
        elif cause_id == RETURN_INFORMATION_BY_REMOTE_COMMAND:
            cause = "return information by remote command"
        else:
            return "ERROR: No cause of transmission was found."
        return (cause, ((cot >> 6) & 0x01), ((cot >> 7) & 0x01))

    def unwrap_information_objects(self, type_id, sequence, asdu_length, asdu, length, offset):
        """
        Unpacks information object(s)/element(s) and their corresponding object information.
        :param type_id: Type of the message as an integer.
        :param sequence: SQ bit as defined in IEC 104.
        :param asdu_length: Amount of objects/elements as an integer.
        :param asdu: Information object(s)/element(s) of an ASDU as a single bytestring.
        :param length: Expected byte length of the information object(s)/element(s).
        :return: List of tuples each containing an information object/element found in the ASDU and \
        the corresponding object information depending on the type identification(see IEC 104 specification for Details). ERROR if failed.
        """
        i = 0
        result = []
        if not type(type_id) is int:
            return "ERROR: The type identification has to be an integer."
        if not sequence in [0,1]:
            return "ERROR: Sequence bit has to be 0 or 1."
        if (not type(asdu_length) is int) or (asdu_length < 1):
            return "ERROR: The ASDU length has to be an integer bigger than 0."
        if not type(asdu) is bytes:
            return "ERROR: The ASDU has to be a bytestring."
        if not type(length) is int:
            return "ERROR: The ASDU byte length has to be an integer."
        if sequence == 1:
            if type_id == M_BO_NA_1:
                if (asdu_length * M_BO_NA_1_LENGTH + INFORMATION_OBJECT_ADDRESS_LENGTH) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu, offset))
                if type(ioa) is str:
                    # At the moment this(as well as other exception catching within the function) is not reachable due to the ASDU being checked to be a bytestring. 
                    # In case it becomes possible in the future the checks are already here but tests have yet to be added.
                   return ioa
                result.append(ioa)
                offset = offset + 3
                while i < asdu_length:
                    bsi = (struct.unpack_from('<s', asdu, offset)[0] + struct.unpack_from('<s', asdu, offset + 1)[0] + struct.unpack_from('<s', asdu, offset + 2)[0] \
                    + struct.unpack_from('<s', asdu, offset + 3)[0]).decode()
                    qds = self.unwrap_quality_descriptor(struct.unpack_from('<B', asdu, offset + 4)[0])
                    if type(qds) is str:
                        return qds
                    result.append((bsi, qds))
                    offset = offset + 5
                    i = i + 1
            elif type_id == M_ME_NC_1:
                if (asdu_length * M_ME_NC_1_LENGTH + INFORMATION_OBJECT_ADDRESS_LENGTH) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu, offset))
                if type(ioa) is str:
                    return ioa
                result.append(ioa)
                offset = offset + 3
                while i < asdu_length:
                    number = struct.unpack_from('<f', asdu, offset)[0]
                    qds = self.unwrap_quality_descriptor(struct.unpack_from('<B', asdu, offset + 4)[0])
                    if type(qds) is str:
                        return qds
                    result.append((number, qds))
                    offset = offset + 5
                    i = i + 1
            else: 
                return "ERROR: The ASDU type was not recognized or does not work as a sequence."
        else:
            if type_id == M_BO_NA_1:
                if (asdu_length * (M_BO_NA_1_LENGTH + INFORMATION_OBJECT_ADDRESS_LENGTH)) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                while i < asdu_length:
                    ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu, offset))
                    if type(ioa) is str:
                        return ioa
                    bsi = (struct.unpack_from('<s', asdu, offset + 3)[0] + struct.unpack_from('<s', asdu, offset + 4)[0] + struct.unpack_from('<s', asdu, offset + 5)[0] \
                    + struct.unpack_from('<s', asdu, offset + 6)[0]).decode()
                    qds = self.unwrap_quality_descriptor(struct.unpack_from('<B', asdu, offset + 7)[0])
                    if type(qds) is str:
                        return qds
                    result.append((ioa, bsi, qds))
                    offset = offset + 8
                    i = i + 1
            elif type_id == M_ME_NC_1:
                if (asdu_length * (M_ME_NC_1_LENGTH + INFORMATION_OBJECT_ADDRESS_LENGTH)) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                while i < asdu_length:
                    ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu, offset))
                    if type(ioa) is str:
                        return ioa
                    number = struct.unpack_from('<f', asdu, offset + 3)[0]
                    qds = self.unwrap_quality_descriptor(struct.unpack_from('<B', asdu, offset + 7)[0])
                    if type(qds) is str:
                        return qds
                    result.append((ioa, number, qds))
                    offset = offset + 8
                    i = i + 1
            elif type_id == C_SC_NA_1:
                if asdu_length != 1:
                    return "ERROR: C_SC_NA_1 expects only one information object."
                if (asdu_length + INFORMATION_OBJECT_ADDRESS_LENGTH) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu, offset))
                if type(ioa) is str:
                    return ioa
                sco = self.unwrap_single_command(struct.unpack_from('<B', asdu, offset + 3)[0])
                if type(sco) is str:
                    return sco
                result.append((ioa, sco))
            elif type_id == C_IC_NA_1:
                if asdu_length != 1:
                    return "ERROR: C_IC_NA_1 expects only one information object."
                if (asdu_length + INFORMATION_OBJECT_ADDRESS_LENGTH) != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu))
                if type(ioa) is str:
                    return ioa
                qoi = self.unwrap_qualifier_of_interrogation(struct.unpack_from('<B', asdu, offset + 3)[0])
                if type(qoi) is str:
                    return qoi
                result.append((ioa, qoi))
            elif type_id == C_RD_NA_1:
                if asdu_length != 1:
                    return "ERROR: C_RD_NA_1 expects only one information object."
                if INFORMATION_OBJECT_ADDRESS_LENGTH != length:
                    return "ERROR: The expected ASDU length does not equal the real length."
                ioa = self.unwrap_information_object_address(struct.unpack_from('<3B', asdu))
                if type(ioa) is str:
                    return ioa
                result.append(ioa)
            else:
                return "ERROR: The ASDU type was not recognized or does only work as a sequence."
        return result

    def unwrap_information_object_address(self, ioa):
        """
        Reads the bits of an IEC 104 information object address.
        :param ioa: Tuple containing with 3 members with bits of the information object address in the following order: lower bits, middle bits, upper bits.
        :return: IEC 104 information object address as an integer. ERROR if failed.
        """
        if (not type(ioa) is tuple) or (len(ioa) != 3) or (not type(ioa[0]) is int) or (not type(ioa[1]) is int) or (not type(ioa[2]) is int):
            return "ERROR: Information object address has to be a tuple containing 3 integers."
        return ioa[0] + (ioa[1] << 8) + (ioa[2] << 16)


    def unwrap_quality_descriptor(self, qds):
        """
        Reads the bits of an IEC 104 quality descriptor from an integer.
        :param qds: Quality descriptor as an integer.
        :return: Tuple containing the overflow bit, the blocked bit, the substituted bit, the not topical bit and the invalid bit in this order. ERROR if failed.
        """
        if not type(qds) is int:
            return "ERROR: The quality descriptor has to be an integer."
        return (qds & 0x01, (qds >> 4) & 0x01, (qds >> 5) & 0x01, (qds >> 6) & 0x01, (qds >> 7) & 0x01)

    def unwrap_single_command(self, sco):
        """
        Reads the bits of an IEC 104 single command from an integer.
        :param sco: Single command as an integer.
        :return: Tuple containing the single command state bit and a qualifier of command. ERROR if failed.
        """
        if not type(sco) is int:
            return "ERROR: A single command has to be an integer."
        qoc = self.unwrap_qualifier_of_command((sco & 0xFC) >> 2)
        return (sco & 0x01, qoc)

    def unwrap_qualifier_of_command(self, qoc):
        """
        Reads the bits of an IEC 104 qualifier of command from an integer.
        :param qoc: Qualifier of command as an integer.
        :return: Tuple containing a qualifier and the S/E bit. ERROR if failed.
        """
        if not type(qoc) is int:
            return "ERROR: Qualifier of command has to be an integer."
        return (qoc & 0x1F, (qoc >> 5) & 0x01)

    def unwrap_qualifier_of_interrogation(self, qualifier):
        """
        Creates an IEC 104 qualifier of interrogation.
        :param qualifier: Number representing an interrogation type as defined in IEC 104.
        :return: IEC 104 qualifier of interrogation as a bytestring. ERROR if failed.
        """
        if (not type(qualifier) is int) or (qualifier < 0) or (qualifier > 255):
            return "ERROR: Qualifier of interrogation has to be an integer between 0 and 255."
        return qualifier

# class TestUnwrapper(unittest.TestCase):

#     def test_unwrap_header(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual(26, unwrapper.unwrap_header(b'\x68\x1A'))
#         self.assertEqual("ERROR: The APDU header has to be a bytestring.", unwrapper.unwrap_header("Test"))
#         self.assertEqual("ERROR: The APDU header has to be exactly 2 bytes long.", unwrapper.unwrap_header(b'\x68\x1A\x11'))
#         self.assertEqual("ERROR: The APDU has to start with a 68H.", unwrapper.unwrap_header(b'\x60\x1A'))

#     def test_unwrap_frame(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual(("i-frame", 32767, 32767), unwrapper.unwrap_frame((254, 255, 254, 255)))
#         self.assertEqual(("s-frame", 1, 32767), unwrapper.unwrap_frame((1, 0, 254, 255)))
#         self.assertEqual(("u-frame", "TESTFR_CON", 0), unwrapper.unwrap_frame((TESTFR_CON, 0, 0, 0)))
#         self.assertEqual(("u-frame", "TESTFR_ACT", 0), unwrapper.unwrap_frame((TESTFR_ACT, 0, 0, 0)))
#         self.assertEqual(("u-frame", "STOPDT_CON", 0), unwrapper.unwrap_frame((STOPDT_CON, 0, 0, 0)))
#         self.assertEqual(("u-frame", "STOPDT_ACT", 0), unwrapper.unwrap_frame((STOPDT_ACT, 0, 0, 0)))
#         self.assertEqual(("u-frame", "STARTDT_CON", 0), unwrapper.unwrap_frame((STARTDT_CON, 0, 0, 0)))
#         self.assertEqual(("u-frame", "STARTDT_ACT", 0), unwrapper.unwrap_frame((STARTDT_ACT, 0, 0, 0)))
#         self.assertEqual(("u-frame", "NO_FUNC", 0), unwrapper.unwrap_frame((NO_FUNC, 0, 0, 0)))
#         self.assertEqual("ERROR: The frame has to be a tuple containing 4 integers.", unwrapper.unwrap_frame((0, 0, 0)))
#         self.assertEqual("ERROR: The frame has to be a tuple containing 4 integers.", unwrapper.unwrap_frame("Test"))
#         self.assertEqual("ERROR: Function type could not be determined.", unwrapper.unwrap_frame((15, 0, 0, 0)))
#         self.assertEqual("ERROR: Frame type could not be determined.", unwrapper.unwrap_frame((21, 0, 0, 0)))

#     def test_unwrap_type_identification(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual("M_BO_NA_1", unwrapper.unwrap_type_identification(M_BO_NA_1))
#         self.assertEqual("M_ME_NC_1", unwrapper.unwrap_type_identification(M_ME_NC_1))
#         self.assertEqual("C_SC_NA_1", unwrapper.unwrap_type_identification(C_SC_NA_1))
#         self.assertEqual("C_IC_NA_1", unwrapper.unwrap_type_identification(C_IC_NA_1))
#         self.assertEqual("C_RD_NA_1", unwrapper.unwrap_type_identification(C_RD_NA_1))
#         self.assertEqual("ERROR: The type identification has to be an integer.", unwrapper.unwrap_type_identification("Test"))
#         self.assertEqual("ERROR: The ASDU type was not recognized.", unwrapper.unwrap_type_identification(-1))

#     def test_unwrap_variable_structure_qualifier(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual((0, 0), unwrapper.unwrap_variable_structure_qualifier(0))
#         self.assertEqual((1, 0), unwrapper.unwrap_variable_structure_qualifier(128))
#         self.assertEqual((0, 127), unwrapper.unwrap_variable_structure_qualifier(127))
#         self.assertEqual("ERROR: The variable structure qualifier has to be an integer.", unwrapper.unwrap_variable_structure_qualifier("Test"))

#     def test_unwrap_cause_of_transmission(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual(("periodic", 0, 0), unwrapper.unwrap_cause_of_transmission(1))
#         self.assertEqual(("spontaneous", 0, 0), unwrapper.unwrap_cause_of_transmission(3))
#         self.assertEqual(("request or requested", 0, 0), unwrapper.unwrap_cause_of_transmission(5))
#         self.assertEqual(("activation", 0, 0), unwrapper.unwrap_cause_of_transmission(6))
#         self.assertEqual(("activation confirmation", 0, 0), unwrapper.unwrap_cause_of_transmission(7))
#         self.assertEqual(("return information by remote command", 0, 0), unwrapper.unwrap_cause_of_transmission(11))
#         self.assertEqual(("periodic", 1, 0), unwrapper.unwrap_cause_of_transmission(65))
#         self.assertEqual(("periodic", 0, 1), unwrapper.unwrap_cause_of_transmission(129))
#         self.assertEqual("ERROR: The cause of transmission, P/N bit and Testit have to be wrapped into an integer.", unwrapper.unwrap_cause_of_transmission("Test"))
#         self.assertEqual("ERROR: No cause of transmission was found.", unwrapper.unwrap_cause_of_transmission(-1))

#     def test_unwrap_quality_descriptor(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual((0, 0, 0, 0, 0), unwrapper.unwrap_quality_descriptor(0))
#         self.assertEqual((1, 0, 0, 0, 0), unwrapper.unwrap_quality_descriptor(1))
#         self.assertEqual((0, 1, 0, 0, 0), unwrapper.unwrap_quality_descriptor(16))
#         self.assertEqual((0, 0, 1, 0, 0), unwrapper.unwrap_quality_descriptor(32))
#         self.assertEqual((0, 0, 0, 1, 0), unwrapper.unwrap_quality_descriptor(64))
#         self.assertEqual((0, 0, 0, 0, 1), unwrapper.unwrap_quality_descriptor(128))
#         self.assertEqual((1, 1, 1, 1, 1), unwrapper.unwrap_quality_descriptor(255))
#         self.assertEqual("ERROR: The quality descriptor has to be an integer.", unwrapper.unwrap_quality_descriptor("Test"))

#     def test_unwrap_qualifier_of_command(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual((0, 0), unwrapper.unwrap_qualifier_of_command(0))
#         self.assertEqual((0, 1), unwrapper.unwrap_qualifier_of_command(32))
#         self.assertEqual((31, 1), unwrapper.unwrap_qualifier_of_command(63))
#         self.assertEqual("ERROR: Qualifier of command has to be an integer.", unwrapper.unwrap_qualifier_of_command("Test"))

#     def test_unwrap_single_command(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual((0, (0, 0)), unwrapper.unwrap_single_command(0))
#         self.assertEqual((1, (0, 0)), unwrapper.unwrap_single_command(1))
#         self.assertEqual((0, (0, 1)), unwrapper.unwrap_single_command(128))
#         self.assertEqual((0, (31, 1)), unwrapper.unwrap_single_command(252))
#         self.assertEqual("ERROR: A single command has to be an integer.", unwrapper.unwrap_single_command("Test"))

#     def test_unwrap_information_object_address(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual(65537, unwrapper.unwrap_information_object_address((1, 0, 1)))
#         self.assertEqual("ERROR: Information object address has to be a tuple containing 3 integers.", unwrapper.unwrap_information_object_address("Test"))
#         self.assertEqual("ERROR: Information object address has to be a tuple containing 3 integers.", unwrapper.unwrap_information_object_address(("Test", 0, 0)))
#         self.assertEqual("ERROR: Information object address has to be a tuple containing 3 integers.", unwrapper.unwrap_information_object_address((0, "Test", 0)))
#         self.assertEqual("ERROR: Information object address has to be a tuple containing 3 integers.", unwrapper.unwrap_information_object_address((0, 0, "Test")))
#         self.assertEqual("ERROR: Information object address has to be a tuple containing 3 integers.", unwrapper.unwrap_information_object_address((0, 0, 0, 0)))

#     def test_unwrap_qualifier_of_interrogation(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual(255, unwrapper.unwrap_qualifier_of_interrogation(255))
#         self.assertEqual("ERROR: Qualifier of interrogation has to be an integer between 0 and 255.", unwrapper.unwrap_qualifier_of_interrogation("Test"))

#     def test_unwrap_information_objects(self):
#         unwrapper = IEC104Unwrapper()

#         # Sequence = 1
#         self.assertEqual([0, ("Test", (0, 0, 0, 0, 0)), ("Test", (1, 0, 0, 0, 0))], \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 1, 2, b'\x00\x00\x00Test\x00Test\x01', 13, 0))
#         self.assertEqual([16777215, ("Test", (0, 0, 0, 0, 0)), ("Test", (1, 0, 0, 0, 0))], \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 1, 2, b'\xFF\xFF\xFFTest\x00Test\x01', 13, 0))
#         # Should be 3.4 but flotaing point errors.. 
#         self.assertEqual([16777215, (3.4000000953674316, (0, 0, 0, 0, 0)), (3.4000000953674316, (1, 0, 0, 0, 0))], \
#             unwrapper.unwrap_information_objects(M_ME_NC_1, 1, 2, b'\xFF\xFF\xFF\x9a\x99\x59\x40\x00\x9a\x99\x59\x40\x01', 13, 0))

#         # Sequence = 0
#         self.assertEqual([(65536, "Test", (0, 0, 0, 0, 0)), (65537, "Test", (0, 0, 0, 0, 0))], \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 0, 2, b'\x00\x00\x01Test\x00\x01\x00\x01Test\x00', 16, 0))
#         # Should be 3.4 but flotaing point errors.. 
#         self.assertEqual([(65536, 3.4000000953674316, (0, 0, 0, 0, 0)), (65537, 3.4000000953674316, (0, 0, 0, 0, 0))], \
#             unwrapper.unwrap_information_objects(M_ME_NC_1, 0, 2, b'\x00\x00\x01\x9a\x99\x59\x40\x00\x01\x00\x01\x9a\x99\x59\x40\x00', 16, 0))
#         self.assertEqual([(65537, (0, (31, 1)))], unwrapper.unwrap_information_objects(C_SC_NA_1, 0, 1, b'\x01\x00\x01\xFC', 4, 0))
#         self.assertEqual([(65537, 255)], unwrapper.unwrap_information_objects(C_IC_NA_1, 0, 1, b'\x01\x00\x01\xFF', 4, 0))
#         self.assertEqual([(65537)], unwrapper.unwrap_information_objects(C_RD_NA_1, 0, 1, b'\x01\x00\x01', 3, 0))
        
#         # Exceptions
#         self.assertEqual("ERROR: The type identification has to be an integer.", unwrapper.unwrap_information_objects("Test", 0, 1, b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: Sequence bit has to be 0 or 1.", unwrapper.unwrap_information_objects(C_RD_NA_1, 10, 1, b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: The ASDU length has to be an integer bigger than 0.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, "Test", b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: The ASDU length has to be an integer bigger than 0.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, -1, b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: The ASDU has to be a bytestring.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, 1, "Test", 3, 0))
#         self.assertEqual("ERROR: The ASDU byte length has to be an integer.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, 1, b'\x01\x00\x01', "Test", 0))
#         self.assertEqual("ERROR: C_SC_NA_1 expects only one information object.", unwrapper.unwrap_information_objects(C_SC_NA_1, 0, 2, b'\x01\x00\x01\xFC', 4, 0))
#         self.assertEqual("ERROR: C_IC_NA_1 expects only one information object.", unwrapper.unwrap_information_objects(C_IC_NA_1, 0, 2, b'\x01\x00\x01\xFF', 4, 0))
#         self.assertEqual("ERROR: C_RD_NA_1 expects only one information object.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, 2, b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: The ASDU type was not recognized or does not work as a sequence.", unwrapper.unwrap_information_objects(-1, 1, 1, b'\x01\x00\x01', 3, 0))
#         self.assertEqual("ERROR: The ASDU type was not recognized or does only work as a sequence.", unwrapper.unwrap_information_objects(-1, 0, 1, b'\x01\x00\x01', 3, 0))
        
#         # Exceptions real length
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 1, 2, b'\x00\x00\x00Test\x00Test\x01', 1, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 1, 2, b'\xFF\xFF\xFFTest\x00Test\x01', 1, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_information_objects(M_ME_NC_1, 1, 2, b'\xFF\xFF\xFF\x9a\x99\x59\x40\x00\x9a\x99\x59\x40\x01', 1, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_information_objects(M_BO_NA_1, 0, 2, b'\x00\x00\x01Test\x00\x01\x00\x01Test\x00', 1, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_information_objects(M_ME_NC_1, 0, 2, b'\x00\x00\x01\x9a\x99\x59\x40\x00\x01\x00\x01\x9a\x99\x59\x40\x00', 1, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", unwrapper.unwrap_information_objects(C_SC_NA_1, 0, 1, b'\x01\x00\x01\xFC', 40, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", unwrapper.unwrap_information_objects(C_IC_NA_1, 0, 1, b'\x01\x00\x01\xFF', 40, 0))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", unwrapper.unwrap_information_objects(C_RD_NA_1, 0, 1, b'\x01\x00\x01', 30, 0))

#     def test_unwrap_apdu(self):
#         unwrapper = IEC104Unwrapper()
#         self.assertEqual((('i-frame', 1, 1), 'M_BO_NA_1', (0, 2), ('periodic', 0, 0), 0, 1, [(0, "Test", (0, 0, 0, 0, 0)), (1, "Test", (0, 0, 0, 0, 0))]), \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x02\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 26))
#         self.assertEqual((('i-frame', 1, 1), 'M_BO_NA_1', (0, 0), ('periodic', 0, 0), 0, 1, "No information objects/elements."), \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x00\x01\x00\x01\x00', 10))
#         self.assertEqual("ERROR: The length has to be an integer bigger than " + str(APDU_MIN_LEN - 1) + "(excluding header).", \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x02\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 9))
#         self.assertEqual("ERROR: The APDU has to be a bytestring.", \
#             unwrapper.unwrap_apdu("Test", 10))
#         self.assertEqual("ERROR: Function type could not be determined.", \
#             unwrapper.unwrap_apdu(b'\x0F\x00\x00\x00\x07\x02\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 26))
#         # This test only needs to be done if one of the integers between 0 and 255 is not assigned to an ASDU type.
#         self.assertEqual("ERROR: The ASDU type was not recognized.", \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\xFF\x02\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 26))
#         # This test only needs to be done if one of the integers between 0 and 63 is not assigned to a cause of transmission.
#         self.assertEqual("ERROR: No cause of transmission was found.", \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x02\x3F\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 26))
#         self.assertEqual("ERROR: No information object was expected but the APDU still contains information.", \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x00\x01\x00\x01\x00\x00\x00\x00Test\x00\x01\x00\x00Test\x00', 26))
#         self.assertEqual("ERROR: The expected ASDU length does not equal the real length.", \
#             unwrapper.unwrap_apdu(b'\x02\x00\x02\x00\x07\x02\x01\x00\x01\x00', 10))



# if __name__ == "__main__":
#     unittest.main()