import json
import lancexagent as agent 

def heyman(incoming):
    return "Hello World!"

def whatup(incoming):
    request = json.loads(incoming)['request']
    print request['body']
    return incoming

def main():
    agent.handleRequest("greeting", heyman)
    agent.handleRequest("loopback", whatup)
    agent.loop()

if __name__ == '__main__':
    main()