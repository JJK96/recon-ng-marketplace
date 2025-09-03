from recon.core.module import BaseModule

class Module(BaseModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'AADInternals Tenant information',
        'author': 'Jan-Jaap Korpershoek (@jjk96)',
        'version': '1.0',
        'description': 'Gathers information about the Azure AD tenant associated with a domain. In addition to tenant information, it also yields associated domains.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL'
    }

    def module_run(self, domains):
        for domain in domains:
            origin = "https://aadinternals.com"
            url = f"https://aadinternals.azurewebsites.net/api/tenantinfo?domainName={domain}"
            self.output(url)
            resp = self.request("GET", url, headers={
                "Origin": origin,
                "Referer": origin + "/"
            })
            self.output(resp)
            self.output(resp.content)
            if resp.status_code != 200:
                self.error(f"Got unexpected response code: {resp.status_code}")
                continue
            data = resp.json()
            self.insert_tenants(
                brand=data.get("tenantBrand", ""),
                name=data.get("tenantName", ""),
                id=data.get("tenantId", ""),
                region=data.get("tenantRegion", ""),
                subregion=data.get("tenantSubRegion", ""),
                domain=data.get("domain", ""),
                desktopSSOEnabled=data.get("desktopSSOEnabled", False),
                CBAEnabled=data.get("CBAEnabled", False),
                usesCloudSync=data.get("usesCloudSync", False)
            )
            for domain in data.get('domains', []):
                self.insert_domains(domain=domain['name'], notes=domain.get('type', ''))

