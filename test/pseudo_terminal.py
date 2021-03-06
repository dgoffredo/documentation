#! /usr/bin/env python3

# Copyright 2019 Oath Inc. Licensed under the terms of the Apache 2.0 license. See LICENSE in the project root.

import os
import re
import sys
import random
import pexpect


class Log:
    def __init__(self):
        self._log = None
        self._filter_pattern = None
        self.reset_log()

    def reset_log(self):
        self._log = []

    def stdout_filter(self, pattern):
        self._filter_pattern = pattern

    def get_log(self):
        return "".join(self._log)

    def write(self, s):
        self._log.append(s)
        if re.match(self._filter_pattern, s) is None:
            sys.stdout.write(s)

    def flush(self):
        sys.stdout.flush()


class PseudoTerminal:
    def __init__(self, timeout=30*60):
        self._log = Log()
        self._pty = None
        self._cmd_timeout = timeout

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        env = os.environ.copy()
        env["PS1"] = ""  # remove default terminal prompt
        env["PS2"] = ""
        self._pty = pexpect.spawn('sh', env=env, echo=False, encoding='utf-8')
        self._pty.logfile_read = self._log

    def stop(self):
        self._pty.close()

    def run(self, command):
        command_id = random.randint(10e4, 10e5)
        sentinel = "sentinel-{0}> exit code: ".format(command_id)
        sentinel_pattern = re.compile(sentinel + "(\d+)")

        self._log.reset_log()
        self._log.stdout_filter(sentinel_pattern)
        self._pty.sendline(command)
        self._pty.sendline("echo \"" + sentinel + "$?\"")

        index = self._pty.expect([sentinel_pattern, pexpect.EOF, pexpect.TIMEOUT], timeout=self._cmd_timeout)
        if index == 0:
            if self._pty.match is not None:
                exit_code = int(self._pty.match.group(1))
                output = self._log.get_log()
                return exit_code, output
            raise RuntimeError("Unexpected state: Found pattern, but not regexp match.")
        if index == 1:
            raise RuntimeError("Unexpected EOF in pseudo-terminal")
        if index == 2:
            raise RuntimeError("Timeout in execution of {}".format(command))
        raise RuntimeError("Unexpected state")

