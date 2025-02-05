from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request

def get_domains(domain):

    # Create a valid HTTP request
    # Example from: https://docs.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxwsadisc/18fe58cd-3761-49da-9e47-84e7b4db36c2
    body = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:exm="http://schemas.microsoft.com/exchange/services/2006/messages" 
        xmlns:ext="http://schemas.microsoft.com/exchange/services/2006/types" 
        xmlns:a="http://www.w3.org/2005/08/addressing" 
        xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Header>
        <a:RequestedServerVersion>Exchange2010</a:RequestedServerVersion>
        <a:MessageID>urn:uuid:6389558d-9e05-465e-ade9-aae14c4bcd10</a:MessageID>
        <a:Action soap:mustUnderstand="1">http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation</a:Action>
        <a:To soap:mustUnderstand="1">https://autodiscover.byfcxu-dom.extest.microsoft.com/autodiscover/autodiscover.svc</a:To>
        <a:ReplyTo>
        <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
        </a:ReplyTo>
    </soap:Header>
    <soap:Body>
        <GetFederationInformationRequestMessage xmlns="http://schemas.microsoft.com/exchange/2010/Autodiscover">
        <Request>
            <Domain>{domain}</Domain>
        </Request>
        </GetFederationInformationRequestMessage>
    </soap:Body>
    </soap:Envelope>"""

    # Including HTTP headers
    headers = {
        "Content-type": "text/xml; charset=utf-8",
        "User-agent": "AutodiscoverClient"
    }

    # Perform HTTP request
    try:
        httprequest = Request(
            "https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc", headers=headers, data=body.encode())

        with urlopen(httprequest) as response:
            response = response.read().decode()
    except Exception:
        print("[-] Unable to execute request. Wrong domain?")
        exit()

    # Parse XML response
    domains = []

    tree = ET.fromstring(response)
    for elem in tree.iter():
        if elem.tag == "{http://schemas.microsoft.com/exchange/2010/Autodiscover}Domain":
            yield elem.text
    
class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'check_mdi',
        'author': 'Northwave',
        'version': '1.0',
        'description': 'Uses the check_mdi script to get more domains for the given tenant. check_mdi: https://github.com/expl0itabl3/check_mdi',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL',
        'options': (),
        'files': [],
    }

    def module_run(self, domains):
        self.thread(domains)

    def module_thread(self, tenant):
        for domain in get_domains(tenant):
            self.insert_domains(domain)


