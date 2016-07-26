import json
import lancexagent as agent 
import time

def greeting(incoming):
    return "Hello, it is now %s" % time.asctime( time.localtime(time.time()) )

def loopback(incoming):
    request = json.loads(incoming)['request']
    print request['body']
    return incoming

def main():
    agent.handleRequest("greeting", greeting)
    agent.handleRequest("loopback", loopback)
    agent.loop()

if __name__ == '__main__':
    main()
