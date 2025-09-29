from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
import dns.resolver
import re

class Module(BaseModule, ResolverMixin):

    meta = {
        'name': 'Find Azure subdomains',
        'author': 'Jan-Jaap Korpershoek (@JJK96)',
        'version': '1.0',
        'description': 'Uses CNAME records of existing hosts to enumerate other Azure resource domains. Loosely based on https://github.com/NetSPI/MicroBurst',
        'comments': (
            'Note: Nameserver must be in IP form.',
        ),
        'query': 'SELECT DISTINCT cname FROM hosts WHERE cname IS NOT NULL',
    }

    domains = [
    	'scm.azurewebsites.net',
    	'azurewebsites.net',
    	'p.azurewebsites.net',
    	'cloudapp.net',
    	'file.core.windows.net',
    	'blob.core.windows.net',
    	'queue.core.windows.net',
    	'table.core.windows.net',
    	'redis.cache.windows.net',
    	'documents.azure.com',
    	'database.windows.net',
    	'vault.azure.net',
    	'azureedge.net',
    	'search.windows.net',
    	'azure-api.net',
    	'azurecr.io',
        'azure.com',
    ]


    def module_run(self, hosts):
        regex = re.compile(r'.*?(' + '|'.join(domain for domain in self.domains) + r')\.$')
        q = self.get_resolver()
        for host in hosts:
            if not regex.match(host):
                continue
            first_part = host.partition('.')[0]
            for domain in self.domains:
                host_to_check = first_part + '.' + domain
                self.verbose(f'Checking {host_to_check}')
                try:
                    answers = q.query(host_to_check)
                except dns.resolver.NXDOMAIN:
                    self.verbose(f"{host_to_check} => Unknown")
                except dns.resolver.NoAnswer:
                    self.verbose(f"{host_to_check} => No answer")
                except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                    self.verbose(f"{host_to_check} => DNS Error")
                else:
                    for i in range(0, len(answers)):
                        data = {
                            'host': host_to_check,
                            'ip_address': answers[0].address
                        }
                        self.insert('hosts', data, list(data.keys()))
                        self.output(f"{host_to_check} => {answers[i].address}")
