#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import pexpect
import commands
import xml.etree.ElementTree as ET
import datetime

PROMPT_REGEX=r"[%$>#]"
PASSWORD_REGEX="(パスワード|Password|password):"

####################################################################################################
# For pexpect.spawn class
def sshConnect(self, username, hostname, key = None, password = None, rootPassword = None):
    """ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/Dropbox/Personal/amazon/amazon_keypair.pem ec2-user@ec2-54-238-180-198.ap-northeast-1.compute.amazonaws.com"""

    options = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    if key == None:
        # without password
        self.sendline("ssh {0} {1}@{2}".format(options, username, hostname))
        index = self.expect([PASSWORD_REGEX, PROMPT_REGEX])
        if index == 0:
            self.sendline(password)
            self.expect(PROMPT_REGEX)
        #
    else:
        # with key
        options = options + " -i " + key
        self.sendline("ssh {0} {1}@{2}".format(options, username, hostname))
        index = self.expect(["passphrase for key.+:", PROMPT_REGEX])
        if index == 0:
            self.sendline(password)
            self.expect(PROMPT_REGEX)
        #
    #
    if rootPassword != None:
        # be root
        self.sendline("su -")
        self.expect(PASSWORD_REGEX)
        self.sendline(rootPassword)
        self.expect(PROMPT_REGEX)
    #
#
pexpect.spawn.sshConnect = sshConnect
#
def exitAll(self):
    try:
        while True:
            self.sendline('exit')
            index = self.expect([PROMPT_REGEX, pexpect.EOF])
            if index == 1:
                break
            #
        #
    except OSError:
        pass
    #
#
pexpect.spawn.exitAll = exitAll
#
####################################################################################################

def getCommandOutput(command, username, password, hostname, key, rootPassword):
    p = pexpect.spawn('/bin/sh')
    p.logfile_read = sys.stdout
    #p.logfile_send = sys.stdout
    p.expect(PROMPT_REGEX)
    
    p.sshConnect(username, hostname, key, password, rootPassword)
    
    p.sendline(command)
    p.expect(PROMPT_REGEX)

    # for debug
    #print("buffer: {0}".format(p.buffer))
    #print("before: {0}".format(p.before))
    #print("after: {0}".format(p.after))

    # get string removed echo-back
    result = p.before[p.before.find('\n') + 1:]
    
    p.exitAll()

    return result
#

def getData():
    xmltree = ET.parse('./Config.xml')
    xmlroot = xmltree.getroot()

    result = {}
    for server in xmlroot.iter('server'):
        name = server.attrib['name']
        username = server.find('username').text
        password = server.find('password').text
        hostname = server.find('hostname').text
        key = server.find('keypath').text
        rootPassword = server.find('rootPassword').text

        result[name] = { }
        for command_elem in server.find('commands').iter('command'):
            command_name = command_elem.attrib['name']
            input_command = command_elem.find('input_command').text

            features = { }
            for feature in command_elem.find('features').iter('feature'):
                features[feature.attrib['name']] = feature.find('extract_command').text
            #
            res = getCommandOutput(input_command, username, password, hostname, key, rootPassword)

            resDir = { }
            #resDir["raw"] = res
            resDir['get_time'] = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            for n, c in features.items():
                r =  commands.getoutput('echo "{0}" | {1}'.format(res, c))
                resDir[n] = r
            #
            result[name][command_name] = resDir
        #
    #
    return result
#

def updateXml2(filename, data):
    if os.path.isfile(filename):
        tree = ET.ElementTree(file=filename)
        xmlroot = tree.getroot()
    else:
        xmlroot = ET.Element('data')
        tree = ET.ElementTree(xmlroot)
    #
    for k1,v1 in data.items():
        server_child = ET.SubElement(xmlroot, 'server')
        server_child.attrib['name'] = k1
        for k2,v2 in v1.items():
            
            command_child = ET.SubElement(server_child, 'command')
            command_child.attrib['name'] = k2
            command_child.attrib['get_time'] = v2['get_time']
            for k3,v3 in v2.items():
                if k3 != 'get_time':
                    feature_child= ET.SubElement(command_child, 'feature')
                    feature_child.attrib['name'] = k3
                    feature_child.text = v3
                #
            #
        #
    #
    tree.write(filename)
#
def updateXml(filename, data):
    def makeXml_recursive(xml, data):
        if isinstance(data, dict):
            # recursively iterate
            for k,v in data.items():
                child = ET.SubElement(xml, k)
                makeXml_recursive(child, v)
            #
        #
        else:
            # set value
            xml.text = data
        #
    #
    if os.path.isfile(filename):
        tree = ET.ElementTree(file=filename)
        xmlroot = tree.getroot()
    else:
        xmlroot = ET.Element('data')
        tree = ET.ElementTree(xmlroot)
    #
    makeXml_recursive(xmlroot, data)

    tree.write(filename)
#
    
if __name__ == '__main__':
    data = getData()

    #print data
    
    filename = 'data2.xml'
    xml = updateXml2(filename, data)
#
