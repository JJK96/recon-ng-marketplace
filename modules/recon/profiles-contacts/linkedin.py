from recon.core.module import BaseModule
from recon.mixins.threads import ThreadingMixin
import requests

class Module(BaseModule, ThreadingMixin):

    meta = {
        'name': 'LinkedIn Parser',
        'author': 'Jan-Jaap Korpershoek (@JJK96)',
        'version': '1.0',
        'description': 'Parse LinkedIn people page to find job description.',
        'dependencies': [],
        'files': [],
        'required_keys': ['linkedin_jsessionid', 'linkedin_li_at'],
        'comments': (
        ),
        'query': 'SELECT url, contact_id FROM profiles WHERE resource = "LinkedIn" and url IS NOT NULL and contact_id IS NOT NULL',
        'options': (
        ),
    }

    def module_run(self, profiles):
        self.thread(profiles)

    def module_thread(self, profile):
        url, contact_id = profile
        resp = requests.get(url, cookies={"JSESSIONID": self.get_key('linkedin_jsessionid'), "li_at": self.get_key("linkedin_li_at")})
        # Text before the job description
        prefix = "&quot;multiLocaleHeadline&quot;:[{&quot;value&quot;:&quot;"
        start = resp.text.index(prefix)
        if start < 0:
            print(f"Job title not found for {url}")
            return
        start += len(prefix)
        # Text after the job description
        length = resp.text[start:].index("&quot")
        job_title = resp.text[start:start+length]
        print(f"Found job title for {url}: {job_title}")
        self.query("update contacts set title = ? where rowid = ?", (job_title, contact_id))
