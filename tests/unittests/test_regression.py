"""
Test regressions with fixed seed
expected files are in the "expected" folder
the filename has pattern pop_{n}_seed{seed}.json

Expected files are generated by running this script with regenerate = True. Once
run, you will need to manually copy the files from

    regression/report/test_regression_make_population/test_results

to
    regression/expected/test_regression_make_population

for the new baseline to take effect.
"""

import os
import sys
import shutil
import fnmatch
import unittest
import tempfile
import numpy as np
import sciris as sc
import synthpops as sp
from synthpops import data_distributions as spdd
from synthpops import base as spb

try:
    from fpdf import FPDF
except Exception as E:
    print(f'Note: could not import fpdf, report not available ({E})')

# import utilities from test directory
testdir = sc.thisdir(__file__, os.pardir)
sys.path.append(testdir)
import utilities

# Whether to remove temporary files generated in the process
remove_files = True

# Whether to regenerate files
regenerate = False


class TestRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.n = 20001
        cls.seed = 1001
        # change this to True if you need to re-generate the baseline
        cls.generateBaseline = regenerate
        cls.pdfDir = sc.thisdir(__file__, "regression", "report")
        cls.expectedDir = sc.thisdir(__file__, "regression", "expected")
        cls.datadir = sc.thisdir(__file__, os.pardir, "data")
        shutil.rmtree(cls.pdfDir, ignore_errors=True)
        os.makedirs(cls.pdfDir, exist_ok=True)

    def setUp(self):
        self.resultdir = tempfile.TemporaryDirectory().name
        self.figDir = os.path.join(self.resultdir, "figs")
        self.configDir = os.path.join(self.resultdir, "configs")
        os.makedirs(self.figDir, exist_ok=True)
        os.makedirs(self.configDir, exist_ok=True)

    def tearDown(self):
        shutil.copytree(self.resultdir, os.path.join(self.reportfolder, "test_results"),
                        ignore=shutil.ignore_patterns("pop*.json", "*pop.json"))
        if remove_files:
            shutil.rmtree(self.resultdir, ignore_errors=True)
        else:
            print(f'Results folder: {self.resultdir}')
            print('Automatic file removing is switched off;\nwhen you are done, please remove it manually')

    @classmethod
    def tearDownClass(cls):
        if cls.generateBaseline:
            print(f"Generated baseline files without comparison.\n please review at {cls.pdfDir} and copy them to {cls.expectedDir}.")

    def test_regression_make_population(self):
        # set params, make sure name is identical to param names
        n = self.n
        rand_seed = self.seed
        location = 'seattle_metro'
        state_location = 'Washington'
        country_location = 'usa'
        max_contacts = None
        with_industry_code = False
        with_facilities = False
        use_two_group_reduction = False
        average_LTCF_degree = 20
        generate = True
        #
        # previously defaults
        # ltcf_staff_age_min = 20
        # ltcf_staff_age_max = 60
        # with_school_types = False
        # school_mixing_type = "random"
        # average_class_size = 20
        # inter_grade_mixing = 0.1
        # average_student_teacher_ratio = 20
        # average_teacher_teacher_degree = 3
        # teacher_age_min = 25
        # teacher_age_max = 75
        # with_non_teaching_staff = False
        # average_student_all_staff_ratio = 15
        # average_additional_staff_degree = 20
        # staff_age_min = 20
        # staff_age_max = 75
        #
        test_prefix = 'test_regression_make_population'
        self.reportfolder = os.path.join(self.pdfDir, test_prefix)
        os.makedirs(self.reportfolder, exist_ok=True)
        filename = os.path.join(self.resultdir, f'pop_{n}_seed{rand_seed}.json')
        actual_vals = locals()
        self.run_regression(filename, test_prefix, actual_vals, location, state_location, country_location)

    @unittest.skip("This is just to show an example of adding a different scenario will work")
    def test_regression_lower_teacher_age(self):
        # set params, make sure name is identical to param names
        n = self.n
        rand_seed = self.seed
        max_contacts = None
        teacher_age_min = 20
        teacher_age_max = 65
        staff_age_min = 18
        staff_age_max = 60
        generate = True
        #
        test_prefix = 'test_regression_lower_teacher_age'
        self.reportfolder = os.path.join(self.pdfDir, test_prefix)
        os.makedirs(self.reportfolder, exist_ok=True)
        filename = os.path.join(self.resultdir, f'pop_{n}_seed{rand_seed}.json')
        actual_vals = locals()
        self.run_regression(filename, test_prefix, actual_vals)

    def run_regression(self, filename, test_prefix, actual_vals, location, state_location, country_location):
        pop = utilities.runpop(resultdir=self.configDir, actual_vals=actual_vals, testprefix=test_prefix,
                               method=sp.make_population)
        # if default sort order is not concerned:
        pop = dict(sorted(pop.items(), key=lambda x: x[0]))
        sc.savejson(filename, pop, indent=2)
        self.get_pop_details(pop, self.resultdir, test_prefix, location, state_location, country_location)
        if not self.generateBaseline:
            unchanged, failed_cases = self.check_result(actual_folder=self.resultdir, test_prefix=test_prefix)
            if unchanged:
                print(f'Note: regression unchanged')
            else:
                print(f'Warning, regression changed! Generating report...')
                self.generate_reports(test_prefix=test_prefix, failedcases=failed_cases)
                errormsg = f"regression test detected changes, " \
                           f"please go to \n{self.pdfDir} " \
                           f"to review report and test results \n " \
                           f"\n\ndelete files in {os.path.join(self.expectedDir, test_prefix)} " \
                           f"and regenerate expected files using cls.generateBaseline=True\n " \
                           f"if you approve this change."
                raise ValueError(errormsg)

    def get_pop_details(self, pop, dir, title_prefix, location, state_location, country_location, decimal=3):
        os.makedirs(dir, exist_ok=True)
        for setting_code in ['H', 'W', 'S']:
            average_contacts = utilities.get_average_contact_by_age(pop, self.datadir, setting_code=setting_code, decimal=decimal)
            fmt = f'%.{str(decimal)}f'
            # print(f"expected contacts by age for {code}:\n", average_contacts)
            utilities.plot_array(average_contacts, datadir = self.figDir,
                                 testprefix=f"{self.n}_seed_{self.seed}_{setting_code}_average_contacts",
                                 expect_label='Expected' if self.generateBaseline else 'Test')
            sc.savejson(os.path.join(dir, f"{self.n}_seed_{self.seed}_{setting_code}_average_contact.json"),
                        dict(enumerate(average_contacts.tolist())), indent=2)

            for method in ['density', 'frequency']:
                matrix = sp.calculate_contact_matrix(pop, method, setting_code)
                brackets = spdd.get_census_age_brackets(self.datadir, state_location, country_location)
                ageindex = spb.get_age_by_brackets_dic(brackets)
                agg_matrix = spb.get_aggregate_matrix(matrix, ageindex)
                textfile = os.path.join(dir, f"{self.n}_seed_{self.seed}_{setting_code}_{method}_contact_matrix.csv")
                np.savetxt(textfile, agg_matrix, delimiter=",", fmt=fmt)
                fig = sp.plot_contacts(pop, setting_code=setting_code, density_or_frequency=method)
                fig.savefig(os.path.join(self.figDir, f"{self.n}_seed_{self.seed}_{setting_code}_{method}_contact_matrix.png"))

    """
    Compare all csv, json files between actual/expected folder
    files must be under "test_prefix" subfolder and have the same name in both folders
    """
    def check_result(self, actual_folder, expected_folder=None, test_prefix="test", decimal=3):
        passed = True
        checked = False
        failed_cases = []
        if not os.path.exists(actual_folder):
            raise FileNotFoundError(actual_folder)
        if expected_folder is None:
            expected_folder = os.path.join(self.expectedDir, test_prefix)
        if not os.path.exists(expected_folder):
            raise FileNotFoundError(f"{expected_folder} does not exist, use cls.generateBaseline = True to generate them")
        for f in os.listdir(expected_folder):
            print(f"\n{f}")
            if f.endswith(".csv"):
                checked = True
                expected_data = np.loadtxt(os.path.join(expected_folder, f), delimiter=",")
                actual_data = np.loadtxt(os.path.join(actual_folder, f), delimiter=",")
                if (np.round(expected_data, decimal) == np.round(actual_data, decimal)).all():
                    print("values unchanged, passed")
                else:
                    passed = False
                    failed_cases.append(os.path.basename(f).replace(".csv", "*"))
                    print("result has been changed in these indexes:\n", np.where(expected_data != actual_data)[0])
            elif f.endswith(".json"):
                expected_data = sc.loadjson(os.path.join(expected_folder, f))
                actual_data = sc.loadjson(os.path.join(actual_folder, f))
                if (expected_data == actual_data):
                    print("values unchanged, passed")
                else:
                    passed = False
                    failed_cases.append(os.path.basename(f).replace(".json", "*"))
                    diff = set(expected_data.items()).symmetric_difference(actual_data.items())
                    print("result has been changed in:\n", diff)
            else:
                print("ignored.\n")
        return passed & checked, failed_cases

    def generate_reports(self, test_prefix="", failedcases=[]):
        # search for config files
        configs = [f for f in os.listdir(self.configDir) if os.path.isfile(os.path.join(self.configDir, f)) and f.endswith("config.json")]
        for c in configs:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            name = os.path.splitext(c)[0]
            contents = ""
            # pdf.cell(w=200, h=10, txt=name, align="C")
            with open(os.path.join(self.configDir, c)) as cf:
                contents = "\n".join([line.strip() for line in cf])
            print(contents)
            pdf.multi_cell(w=100, h=5, txt=contents)
            figs = [f for f in os.listdir(self.figDir) if f.endswith("png")]
            print(f"failed cases:{failedcases}")
            for ff in figs:
                print(f"checking:{ff}")
                for fc in failedcases:
                    if fnmatch.fnmatch(ff, fc):
                        print(f"matching {fc} -> {ff}")
                        pdf.add_page()
                        pdf.image(os.path.join(self.expectedDir, test_prefix, "figs", ff), w=100, h=100)
                        pdf.image(os.path.join(self.figDir, ff), w=100, h=100)
                        break
            pdf.output(os.path.join(self.pdfDir,f"{name}.pdf"))
            print("report generated:", os.path.join(self.pdfDir,f"{name}.pdf"))

    def check_similarity(self, actual, expected):
        """
        Compare two population dictionaries using contact matrix
        Assuming the canberra distance should be small
        """
        passed = True
        checked = False
        for code in ['H', 'W', 'S']:
            # check average contacts per age, if difference is small enough to tolerate
            expected_contacts = utilities.get_average_contact_by_age(expected, self.datadir, code=code)
            print("expected contacts by age:\n", expected_contacts)
            np.savetxt(os.path.join(self.pdfDir,f"pop{self.n}_seed_{self.seed}_{code}_average_contact.csv"), expected_contacts, delimiter=",")
            actual_contacts = utilities.get_average_contact_by_age(actual, self.datadir, code=code)
            print("actual contacts by age:\n", actual_contacts)
            max_difference = np.abs(expected_contacts-actual_contacts).max()
            checked = True
            print(f"max_difference for contacts {code} in each age bracket:{max_difference}\n")
            if max_difference > 1:
                for option in ['density', 'frequency']:
                    print(f"\ncheck:{code} with {option}")
                    actual_matrix = sp.calculate_contact_matrix(actual, density_or_frequency=option, setting_code=code)
                    # expected_matrix = sp.calculate_contact_matrix(expected, density_or_frequency=option, setting_code=code)
                    expected_matrix = np.loadtxt(os.path.join(self.expectedDir,f"pop{self.n}_seed_{self.seed}_{code}_{option}_contact_matrix.csv"), unpack=True, delimiter=",")
                    np.savetxt(os.path.join(self.pdfDir,f"pop{self.n}_seed_{self.seed}_{code}_{option}_contact_matrix.csv"), expected_matrix, delimiter=",")
                    # calculate Canberra distance
                    # assuming they should round to 0
                    d = np.abs(expected_matrix - actual_matrix).mean()
                    # d = distance.canberra(actual_matrix.flatten(), expected_matrix.flatten())
                    print(f"mean absolute difference between actual/expected contact matrix for {code}/{option} is {str(round(d, 3))}")
                    if d > 1:
                        passed = passed & False
        return checked & passed

    def cast_uid_toINT(self, dict):
        return {int(key): val for key, val in dict.items()}


# Run unit tests if called as a script
if __name__ == '__main__':
    unittest.main()
