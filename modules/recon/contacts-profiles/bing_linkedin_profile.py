from recon.core.module import BaseModule
from recon.mixins.search import BingAPIMixin
from recon.utils.parsers import parse_name
from recon.mixins.threads import ThreadingMixin
import re

class Module(BaseModule, BingAPIMixin, ThreadingMixin):

    meta = {
        'name': 'Find Linkedin Profile',
        'author': 'Jan-Jaap Korpershoek, Joe Black (@MyChickenNinja), @fullmetalcache, and Brian King',
        'version': '1.0',
        'description': 'Enriches profiles based on LinkedIn data by querying the Bing API cache for LinkedIn pages related to the given contact, and updates the \'profiles\' table. The module will mainly updated the job title. The user\'s title is then updated in the \'contacts\' table. This module does not access LinkedIn at any time.',
        'required_keys': ['bing_api'],
        'comments': (
            'Be sure to set the \'SUBDOMAINS\' option to the region your target is located in.',
            'You will get better results if you use more subdomains other than just \'www\'.',
            'Multiple subdomains can be provided in a comma separated list.',
            'Results will include historical associations, not just current employees.',
        ),
        'query': 'SELECT DISTINCT rowid, first_name, middle_name, last_name FROM contacts WHERE first_name IS NOT NULL and last_name IS NOT NULL',
        'options': (
            ('limit', 0, True, 'limit total number of pages per api request (0 = unlimited)'),
            ('subdomains', None, False, 'subdomain(s) to search on LinkedIn: www, ca, uk, etc.'),
            ('companies', None, False, 'companies to search for on LinkedIn'),
        ),
    }

    def module_run(self, contacts):
        self.thread(contacts)

    def module_thread(self, contact):
        subdomains = self.options['subdomains']
        subdomain_list = [''] if not subdomains else [x.strip()+'.' for x in subdomains.split(',')]
        name = self.get_name(contact)
        row = contact[0]
        for subdomain in subdomain_list:
            companies = self.options['companies']
            companies = None if not companies else companies.split(',')
            base_query = f'site:"{subdomain}linkedin.com/in/" "{name}"'
            result, company = self.get_result(base_query, companies)
            if result:
                url      = result['displayUrl']
                snippet  = result['snippet']
                cache    = (name,snippet,url,company)
                self.get_contact_info(cache, row)

    def get_result(self, base_query, companies):
        if not companies:
            companies = [None]
        for company in companies:
            results = self.get_result_company(base_query, company)
            if results:
                return results[0], company
        return None, company

    def get_result_company(self, base_query, company):
        if not company:
            query = base_query
        else:
            query = base_query + f' "{company}"'
        return self.search_bing_api(query, self.options['limit'])

    def get_name(self, contact):
        name = contact[1]
        if contact[2]:
            name += " " + contact[2]
        name += " " + contact[3]
        return name
        
    def parse_username(self, url):
        username = None
        username = url.split("/")[-1]
        return username

    def get_contact_info(self, cache, row):
        (name, snippet, url, company) = cache
        fullname, fname, mname, lname = self.parse_fullname(name)
        if fname is None or 'LinkedIn' in fullname or 'profiles' in name.lower() or re.search('^\d+$',fname): 
            # if 'name' has these, it's not a person.
            pass
        elif '\\u2013' in snippet:
            # unicode hyphen between dates here usually means no longer at company.
            # Not always, but nothing available seems more consistent than that.
            pass
        else:
            username = self.parse_username(url)
            jobtitle = self.parse_jobtitle(company, snippet)
            self.query('UPDATE contacts SET title=? WHERE rowid=?', (jobtitle, row))
            self.insert_profiles(username=username, url=url, resource='LinkedIn', category='social', contact_id=row)

    def parse_fullname(self, name):
        fullname = name.split(" -")[0]
        fullname = fullname.split(" |")[0]
        fullname = fullname.split(",")[0]
        fname, mname, lname = parse_name(fullname)
        return fullname, fname, mname, lname

    def parse_jobtitle(self, company, snippet):
        # sample 'snippet' strings with titles. (all contain this string: ' at ')
        # "John Doe. Director of QA at companyname. Location New York, New York Industry Electrical/Electronic Manufacturing"
        # "View John Doe\u2019s professional profile on LinkedIn. ... New Products Curator at companyname. Jane Doe. Sales Operations Analyst at othercompany", 

        # sample 'snippet' strings that are troublemakers
        # View John Doe\u2019s professional profile on ... children will have jobs. ... Security Researcher and Consultant at companyname. Jack ..."

        # sample 'snippet' strings with *no* titles. (none contain this string: ' at ')
        # "View John Doe\u2019s professional profile on LinkedIn. LinkedIn is the world's largest business network, helping professionals like John Doe ...", 
        # "View John Doe\u2019s professional profile on LinkedIn. ... companyname; Education: Carnegie Mellon University; 130 connections. View John\u2019s full profile."

        # outliers (contain a title, but we don't detect it)
        # Jane Doe. cfo, acompanyname. Location Greater New York City Area Industry Electrical/Electronic Manufacturing"

        company = company[:5].lower()   # if no variant of company name in snippet, then no title.
        jobtitle = 'Undetermined'       # default if no title found
        chunks   = snippet.split('...') # if more than one '...' then no title or can't predict where it is
        if ' at ' in snippet and not 'See who you know' in snippet and company in snippet.lower() and len(chunks) < 3:
            if re.search('^View ', snippet):    # here we want the string after " ... " and before " at "
                m = re.search('\.{3} (?P<title>.+?) at ', snippet)
            else:                                   # here we want the string after "^$employeename. " and before " at "
                m = re.search('^[^.]+. (?P<title>.+?) at ', snippet)
            try:
                jobtitle = m.group('title')
            except AttributeError:
                pass
        return jobtitle

