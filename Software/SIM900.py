# -*- coding: utf-8 -*-

import time
import serial


class SIM900(object):
    def __init__(self, port):
        self.baud_rate = 115200
        self.default_timeout = 0.001
        self._timeout = self.default_timeout
        self.ser = serial.Serial(port, self.baud_rate, timeout=self.timeout)
        self.cmd = ""
        self.ans = ""
        self.ret = []
        self.echoed = False
        self.OK = False
        self.communicating = False
        self.listening = False

    def __del__(self):
        self.ser.close()

    @property
    def read_size(self):
        return int(self.baud_rate / 8 * self.timeout) + 1

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, val):
        self._timeout = val
        self.ser.timeout = val

    def reset_timeout(self):
        self.timeout = self.default_timeout

    @property
    def r(self):
        if not self.ret:
            return "Echo:" + str(self.echoed) + \
                   ",OK:" + str(self.OK) + \
                   ",Ans:'" + self.ans.replace("\n", "\\n").replace("\r", "\\r") + "'"
        elif len(self.ret) > 1:
            return "\\n".join(self.ret)
        elif self.ret[0].find(': ') > 0:
            return self.ret[0].split(": ")[1]
        else:
            return self.ret[0]

    def get_ret(self, max_wait=1.0, listener=False, wait_for_transfer_end=False):
        # self.cmd = self.cmd.replace("\n", "").replace("\r", "")
        if self.listening and not listener:
            print "Attempt to read while listening"
            return False

        self.ret = []
        self.OK = False
        self.echoed = False
        self.ans = ""

        # Read data
        self.communicating = True

        wait_begin = time.time()
        while not self.ans:  # Waiting for 1st byte
            self.ans += self.ser.read()
            if time.time() > wait_begin + max_wait:
                self.communicating = False
                return False

        silence_threshold = 5

        if wait_for_transfer_end:  # Wait for data for the entire timeout
            self.timeout = max_wait / silence_threshold

        skipped = 0
        while skipped < silence_threshold:
            new_data = self.ser.read(self.read_size)  # delays for reading
            if not new_data:
                skipped += 1
                # print "skip", skipped
                continue
            self.ans += new_data
            # print "add: '" + new_data.replace("\n", "\\n").replace("\r", "\\r") + "'"
            skipped = 0

        if wait_for_transfer_end:
            self.reset_timeout()

        self.communicating = False
        # End reading

        if not self.ans:
            return False
        for line in self.ans.split("\r"):
            clean_line = line.replace("\n", "")
            if clean_line == self.cmd:
                self.echoed = True
            elif clean_line == "OK":
                self.OK = True
            elif len(clean_line) > 0:
                self.ret.append(clean_line)
        return self.ret

    def AT(self, cmd="", safe=False, wait_for_data=0.0):
        if safe:
            self._stop_listening()
        elif self.listening:
            print "Attempt to send while listening"
            return False
        self.cmd = "AT" if len(cmd) == 0 else "AT+" + cmd
        self.ser.write(self.cmd + "\r")
        if not wait_for_data:
            self.get_ret()  # The quick response
        else:
            try:
                val = float(wait_for_data)
                if val <= 0.0:
                    raise ValueError
                self.get_ret(val, wait_for_transfer_end=True)  # The full response
            except ValueError:
                self.get_ret(1, wait_for_transfer_end=True)  # The default full response with 1s delay
        if safe:
            self.listening = True
        return self.OK

    def _stop_listening(self):
        self.listening = False
        while self.communicating:
            pass
        return

    def safe(self, f, *args):
        self._stop_listening()
        r = f(*args)
        self.listening = True
        return r

    def SMS(self, number, text):
        if not self.AT("CMGF=1"):
            print "Is anything works?"
            return False

        self.AT('CMGS="' + str(number) + '"')
        try:
            if self.ret[0] != '> ':
                self.cmd = str(chr(27))
                self.ser.write(self.cmd)  # Escape
                print "Sending '" + text + "' to '" + str(number) + "' FAILED: " + str(self.r)
                return False
        except IndexError:
            self.cmd = str(chr(27))
            self.ser.write(self.cmd)  # Escape            
            print "Sending '" + text + "' to '" + str(number) + "' FAILED: " + str(self.r)
            return False

        self.cmd = text + chr(26)
        self.ser.write(self.cmd)

        self.get_ret()
        if self.echoed:
            print "Sending '" + text + "' to '" + str(number) + "'...",
        else:
            print "Sending '" + text + "' to '" + str(number) + "' FAILED while typing message: " + str(self.ret)
            self.cmd = str(chr(27))
            self.ser.write(self.cmd)  # Escape
            return False

        self.get_ret(10)  # wait for real answer (typically about 4s)

        ans = self.ret[0]
        if ans.count("CMGS") > 0:
            mr = ans.split(": ")[1]
            print "SUCCESS!!! Message Reference:" + mr
            return mr

        return False


    @staticmethod
    def decode_utf8(byte_string):
        return ''.join([unichr(int(byte_string[i:i+4], 16)) for i in range(0, len(byte_string), 4)])

    @staticmethod
    def encode_utf8(text):
        return ''.join([("%X" % ord(c)).zfill(4) for c in text])

    def USSD(self, number):
        if self.AT('CUSD=1, "' + number + '"'):
            if self.r == "4":
                print "Something went wrong while requesting " + number + ": " + s.ret[0]
                return False
            elif self.r == "ERROR":
                print "Invalid input or USSD"
                return False
            elif self.echoed and self.OK:
                print "USSD Request to " + number + " is processing...",
            else:
                print "Is anything works?"
                return False

        if not self.get_ret(20):  # wait for real answer (typically about 10s)
            print "Timeout =("
            return False

        print "SUCCESS!!!"
        ans = self.ret[0]
        ret = ans.split(",")[1].replace('"', '')
        ret = self.decode_utf8(ret)
        return ret

    def ballance(self):
        for i in range(3):
            ans = self.USSD("*105#")
            if ans:
                print "USSD Answer: " + ans
                ret = ans.split("OCTATOK ")[1].split(" p.")[0]
                return float(ret)

    def _process_SMS(self, sms, asText=True):
        if len(sms) != 2:
            print "SMS not found"
            return False
        meta = sms[0].split('","')
        text = sms[1]

        if len(meta) == 4:
            status, sender, mystic_field, date = meta
        elif len(meta) == 3:
            status, mystic_field, date = meta
            sender = "Unknown"

        else:
            return None, None, "\\n".join(sms)

        status = status.split('"')[1]
        date = date.split('"')[0]

        try:
            for c in text: int(c, 16)
        except ValueError:  # text string
            pass
        else:  # unicode string
            text = self.decode_utf8(text)

        SMS = status, date, mystic_field, sender, text
        sms = self._SMS_ar2txt(SMS)
        print sms
        return sms if asText else SMS

    @staticmethod
    def _SMS_ar2txt(array):
        status, date, mystic_field, sender, text = array
        return "SMS(" + status + ")[" + date + "," + mystic_field + "," + sender + "]: " + text

    def read_SMS(self, n="ALL", as_text=True, leave_unread=False):
        if not self.AT("CMGF=1"):  # Switch from PDU
            print "Is anything works?"
            return False

        if type(n) is not str or len(n) == 1:  # Single reading
            self.AT("CMGR=%s,%d" % (str(n), int(leave_unread)), wait_for_data=0.5)
            return self._process_SMS(self.ret, as_text)
        else:   # Batch reading
            self.AT('CMGL="%s",%d' % (n, int(leave_unread)), wait_for_data=1)
            return [self._process_SMS((self.ret[i], self.ret[i+1]), as_text) for i in range(0, len(self.ret), 2)]

    def del_SMS(self, scope, n=None):
        if scope == scopeOne:
            if n is None:
                print "SMS to delete was not specified"
                return False
        elif type(scope) is str:
            self.AT('CMGDA="DEL ' + str(scope) + '"', wait_for_data=1)
        else:
            self.AT('CMGD=1,' + str(scope), wait_for_data=1)
        return self.OK

# Constants for del_SMS(scope)
scopeOne = 0
scopeRead = 1
scopeReadAndSent = 3
scopeAll = 4

if __name__ == "__main__":
    s = SIM900("COM4")
    if s.AT():
        s.AT("GMM")
        print "Connected to " + s.r
    else:
        print "Failed to connect to SIM900"
        exit()
