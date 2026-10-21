import copy
import unittest

from core.contracts import ContractError, normalize_city, validate_job, validate_profile


def profile():
    return {'schema_version':'1.0','candidate_id':'fictional-a','name':'Nguyễn Thị Minh Anh',
            'language':'vi','preferences':{'salary':{'amount':None,'currency':None,'period':None,
            'gross_net':None,'bonus':None}},'facts':[{'id':'F1','field':'skill','value':'SQL',
            'claim':'Used SQL in a fictional project.','source_id':'CV1','quote':'Used SQL in a fictional project.',
            'locator':'line 3','status':'confirmed','conflict_key':None}]}


def job():
    return {'schema_version':'1.0','platform':'manual','platform_job_id':'fictional-1',
            'employer':'Example Cooperative','req_id':'EX-1','title':'Data Analyst',
            'url':'https://jobs.example.test/EX-1','city':'TP. Hồ Chí Minh','country':'VN',
            'work_model':'onsite','employment_type':'full_time','document_language':'en',
            'raw_jd':'Fictional posting: SQL required.','liveness':'active','readable':True,
            'requirements':[{'id':'R1','text':'SQL','field':'skill','value':'SQL','mandatory':True,'hard':False}],
            'salary':{'amount':None,'currency':None,'period':None,'gross_net':None,'bonus':None}}


class ContractTests(unittest.TestCase):
    def test_unicode_and_unknown_salary_are_preserved_without_conversion(self):
        self.assertEqual('Nguyễn Thị Minh Anh', validate_profile(profile())['name'])
        value=job(); result=validate_job(value)
        self.assertEqual(value['city'], result['city'])
        self.assertIsNone(result['salary']['amount'])
        self.assertEqual('ho chi minh city', normalize_city(value['city']))

    def test_version_and_unknown_fields_are_not_silently_accepted(self):
        for field,value in [('schema_version','99'),('extra','ignored')]:
            item=profile();item[field]=value
            with self.assertRaises(ContractError):validate_profile(item)

    def test_scalar_types_bool_amount_and_invalid_units_are_rejected(self):
        for change in [{'amount':True},{'amount':-1},{'period':'weekly'},{'gross_net':'take-home-ish'}]:
            item=job();item['salary'].update(change)
            with self.assertRaises(ContractError):validate_job(item)
        item=job();item['readable']='yes'
        with self.assertRaises(ContractError):validate_job(item)

    def test_requirement_ids_and_evidence_quote_contract(self):
        item=job();item['requirements']*=2
        with self.assertRaises(ContractError):validate_job(item)
        item=profile();item['facts'][0]['claim']='Expert SQL architect'
        with self.assertRaises(ContractError):validate_profile(item)

    def test_urls_with_credentials_and_unsupported_languages_are_rejected(self):
        item=job();item['url']='https://user:password'+'@'+'jobs.example.test/a'
        with self.assertRaises(ContractError):validate_job(item)
        item=profile();item['language']='auto'
        with self.assertRaises(ContractError):validate_profile(item)
