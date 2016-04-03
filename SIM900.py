# -*- coding: utf-8 -*-

import time
import serial


class SIM900:
    def __init__(self):
        self.baud_rate = 115200
        self._timeout = 0.001
        self.ser = serial.Serial("COM4", self.baud_rate, timeout=self.timeout)
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

    @property
    def r(self):
        if not self.ret:
            return "Echo:" + str(self.echoed) + \
                   ", OK:" + str(self.OK) + \
                   ", Ans:" + self.ans.replace("\n", "\\n").replace("\r", "\\r")
        elif len(self.ret) > 1:
            return "\\n".join(self.ret)
        elif self.ret[0].find(': ') > 0:
            return self.ret[0].split(": ")[1]
        else:
            return self.ret[0]

    def _read_ans(self, max_wait, listener):
        if self.listening and not listener:
            print "Attempt to read while listening"
            return False
        self.ans = ""
        skipped = 0

        wait_begin = time.time()
        while not self.ans:  # Waiting for 1st byte
            self.ans += self.ser.read()
            if time.time() > wait_begin + max_wait:
                return False

        while skipped < 5:
            new_data = self.ser.read(self.read_size)  # delays for reading
            if not new_data:
                skipped += 1
                continue
            self.ans += new_data
            skipped = 0
        return self.ans

    def get_ret(self, max_wait=1, listener=False):
        # self.cmd = self.cmd.replace("\n", "").replace("\r", "")
        self.ret = []
        self.OK = False
        self.echoed = False
        self.communicating = True
        ans = self._read_ans(max_wait, listener)
        self.communicating = False
        if not ans:
            return False
        for line in self.ans.split("\r"):
            clean_line = line.replace("\n", "")
            if clean_line == self.cmd:
                self.echoed = True
            elif clean_line == "OK":
                self.OK = True
            elif len(clean_line) > 0:
                self.ret.append(clean_line)
        return self.OK

    def AT(self, cmd="", safe=False):
        if safe:
            self._stop_listening()
        elif self.listening:
            print "Attempt to send while listening"
            return False
        self.cmd = "AT" if len(cmd) == 0 else "AT+" + cmd
        self.ser.write(self.cmd + "\r")
        self.get_ret()
        if safe:
            self.listening = True
        return self.OK

    def _stop_listening(self):
        self.listening = False
        while self.communicating:
            pass
        return

    def SMS(self, number, text):
        self._stop_listening()
        r = self._unsafe_SMS(number, text)
        self.listening = True
        return r

    def _unsafe_SMS(self, number, text):
        if not self.AT("CMGF=1"):
            print "Is anything works?"
            return False

        self.AT('CMGS="' + str(number) + '"')
        if self.ret[0] != "> ":
            self.ser.write(chr(27))  # Escape
            print "Sending '" + text + "' to '" + str(number) + "' FAILED: " + str(self.ret)
            return False

        self.ser.write(text + chr(26))

        self.get_ret()
        if self.echoed:
            print "Sending '" + text + "' to '" + str(number) + "'...",
        else:
            print "Sending '" + text + "' to '" + str(number) + "' FAILED while typing message: " + str(self.ret)
            self.ser.write(chr(27))  # Escape
            return False

        self.get_ret(10)  # wait for real answer (typically about 4s)

        ans = self.ret[0]
        if ans.count("CMGS") > 0:
            print "SUCCESS!!! Message Reference:" + ans.split(": ")[1]
            return True

        return False

    def USSD(self, number):
        self._stop_listening()
        r = self._unsafe_USSD(number)
        self.listening = True
        return r

    def _unsafe_USSD(self, number):
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
        ret = ''.join([unichr(int(ret[i:i+4], 16)) for i in range(0, len(ret), 4)])  # that was hard
        return ret

    def ballance(self):
        for i in range(3):
            ans = self.USSD("*105#")
            if ans:
                print "USSD Answer: " + ans
                ret = ans.split("OCTATOK ")[1].split(" p.")[0]
                return float(ret)


if __name__ == "__main__":
    s = SIM900()
    if s.AT():
        s.AT("GMM")
        print "Connected to " + s.r
    else:
        print "Failed to connect to SIM900"
        exit()

    import smspdu

    s.AT("CMGR=5,0")
    if not s.ret:
        s.get_ret()  # Actual read
    if len(s.ret) > 1:
        tpdu = s.ret[1]
        pdu = smspdu.SMS_DELIVER.fromPDU(tpdu, "None")
        print pdu.user_data


    pass