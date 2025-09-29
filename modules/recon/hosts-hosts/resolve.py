from recon.core.module import BaseModule
from recon.mixins.resolver import ResolverMixin
import dns.resolver

class Module(BaseModule, ResolverMixin):

    meta = {
        'name': 'Hostname Resolver',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Resolves the IP address for a host. Updates the \'hosts\' table with the results.',
        'comments': (
            'Note: Nameserver must be in IP form.',
        ),
        'query': 'SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL AND ip_address IS NULL',
    }

    def module_run(self, hosts):
        q = self.get_resolver()
        for host in hosts:
            try:
                answers = q.query(host)
            except dns.resolver.NXDOMAIN:
                cname = str(q.canonical_name(host))
                if cname != host + '.':
                    self.verbose(f"'{host + '.'}' -> '{cname}'")
                    note = 'takeover?'
                    self.query('UPDATE hosts SET cname=?, notes=? WHERE host=?', (note, cname, host))
                else:
                    self.verbose(f"{host} => Unknown")
            except dns.resolver.NoAnswer:
                self.verbose(f"{host} => No answer")
            except (dns.resolver.NoNameservers, dns.resolver.Timeout):
                self.verbose(f"{host} => DNS Error")
            else:
                cname = answers.canonical_name.to_text()
                for i in range(0, len(answers)):
                    if i == 0:
                        self.query('UPDATE hosts SET cname=?,ip_address=? WHERE host=?', (cname, answers[i].address, host))
                    else:
                        data = {
                            'host': host,
                            'cname': cname,
                            'ip_address': answers[i].address
                        }
                        self.insert('hosts', data, list(data.keys()))
                    if cname == host + '.':
                        self.output(f"{host} => {answers[i].address}")
                    else:
                        self.output(f"{host} => {cname} => {answers[i].address}")
