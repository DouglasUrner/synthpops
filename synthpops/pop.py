"""
This module provides the layer for communicating with the agent-based model Covasim.
"""

import sciris as sc
import synthpops as sp
from .config import logger as log
from . import config as cfg


class Pop(sc.prettyobj):

    def __init__(self, n=None, max_contacts=None, with_industry_code=False, with_facilities=False,
                    use_two_group_reduction=True, average_LTCF_degree=20, ltcf_staff_age_min=20, ltcf_staff_age_max=60,
                    with_school_types=False, school_mixing_type='random', average_class_size=20, inter_grade_mixing=0.1,
                    average_student_teacher_ratio=20, average_teacher_teacher_degree=3, teacher_age_min=25, teacher_age_max=75,
                    with_non_teaching_staff=False,
                    average_student_all_staff_ratio=15, average_additional_staff_degree=20, staff_age_min=20, staff_age_max=75,
                    rand_seed=None, country_location=None, state_location=None, location=None,
                    do_make=True):
        '''
        Make a full population network including both people (ages, sexes) and contacts using Seattle, Washington data.

        Args:
            n (int)                                 : The number of people to create.
            max_contacts (dict)                     : A dictionary for maximum number of contacts per layer: keys must be "W" (work).
            with_industry_code (bool)               : If True, assign industry codes for workplaces, currently only possible for cached files of populations in the US.
            with_facilities (bool)                  : If True, create long term care facilities, currently only available for locations in the US.
            use_two_group_reduction (bool)          : If True, create long term care facilities with reduced contacts across both groups.
            average_LTCF_degree (float)             : default average degree in long term care facilities.
            ltcf_staff_age_min (int)                : Long term care facility staff minimum age.
            ltcf_staff_age_max (int)                : Long term care facility staff maximum age.
            with_school_types (bool)                : If True, creates explicit school types.
            school_mixing_type (str or dict)        : The mixing type for schools, 'random', 'age_clustered', or 'age_and_class_clustered' if string, and a dictionary of these by school type otherwise.
            average_class_size (float)              : The average classroom size.
            inter_grade_mixing (float)              : The average fraction of mixing between grades in the same school for clustered school mixing types.
            average_student_teacher_ratio (float)   : The average number of students per teacher.
            average_teacher_teacher_degree (float)  : The average number of contacts per teacher with other teachers.
            teacher_age_min (int)                   : The minimum age for teachers.
            teacher_age_max (int)                   : The maximum age for teachers.
            with_non_teaching_staff (bool)          : If True, includes non teaching staff.
            average_student_all_staff_ratio (float) : The average number of students per staff members at school (including both teachers and non teachers).
            average_additional_staff_degree (float) : The average number of contacts per additional non teaching staff in schools.
            staff_age_min (int)                     : The minimum age for non teaching staff.
            staff_age_max (int)                     : The maximum age for non teaching staff.
            rand_seed (int)                         : Start point random sequence is generated from.
            location                  : name of the location
            state_location (string)   : name of the state the location is in
            country_location (string) : name of the country the location is in
            sheet_name                : sheet name where data is located
            do_make (bool): whether to make the population

        Returns:
            network (dict): A dictionary of the full population with ages and connections.
        '''
        log.debug('Pop()')

        # Assign all the variables
        self.school_pars = sc.objdict()
        self.ltcf_pars = sc.objdict()
        self.n                               = n
        self.max_contacts                    = max_contacts
        self.with_industry_code              = with_industry_code
        self.rand_seed                       = rand_seed
        self.country_location                = country_location
        self.state_location                  = state_location
        self.location                        = location
        self.ltcf_pars.with_facilities                 = with_facilities
        self.ltcf_pars.use_two_group_reduction         = use_two_group_reduction
        self.ltcf_pars.average_LTCF_degree             = average_LTCF_degree
        self.ltcf_pars.ltcf_staff_age_min              = ltcf_staff_age_min
        self.ltcf_pars.ltcf_staff_age_max              = ltcf_staff_age_max
        self.school_pars.with_school_types               = with_school_types
        self.school_pars.school_mixing_type              = school_mixing_type
        self.school_pars.average_class_size              = average_class_size
        self.school_pars.inter_grade_mixing              = inter_grade_mixing
        self.school_pars.average_student_teacher_ratio   = average_student_teacher_ratio
        self.school_pars.average_teacher_teacher_degree  = average_teacher_teacher_degree
        self.school_pars.teacher_age_min                 = teacher_age_min
        self.school_pars.teacher_age_max                 = teacher_age_max
        self.school_pars.with_non_teaching_staff         = with_non_teaching_staff
        self.school_pars.average_student_all_staff_ratio = average_student_all_staff_ratio
        self.school_pars.average_additional_staff_degree = average_additional_staff_degree
        self.school_pars.staff_age_min                   = staff_age_min
        self.school_pars.staff_age_max                   = staff_age_max


        # Handle more initialization
        if self.rand_seed is not None:
            sp.set_seed(self.rand_seed)

        default_max_contacts = {'W': 20}  # this can be anything but should be based on relevant average number of contacts for the population under study

        self.n = int(self.n)
        self.max_contacts = sc.mergedicts(default_max_contacts, self.max_contacts)

        # Handle data
        if self.country_location is None :
            self.country_location = cfg.default_country
            self.state_location = cfg.default_state
            self.location = cfg.default_location

        else:
            print(f"========== setting country location = {country_location}")
            cfg.set_location_defaults(country_location)
        # if country is specified, and state is not, we are doing a country population
        if self.state_location is None:
            self.location = None

        self.sheet_name = cfg.default_sheet_name
        self.datadir = sp.datadir # Assume this has been reset...

        # Heavy lift 1: make the contacts and their connections
        log.debug('Generating a new population...')
        population = self.generate()

        # Change types
        for key, person in population.items():
            for layerkey in population[key]['contacts'].keys():
                population[key]['contacts'][layerkey] = list(population[key]['contacts'][layerkey])

        self.popdict = population
        log.debug('Pop(): done.')
        return


    def generate(self, verbose=False):
        ''' Actually generate the network '''

        log.debug('generate_microstructure_with_facilities()')

        # Grab Long Term Care Facilities data
        ltcf_df = spdata.get_usa_long_term_care_facility_data(datadir, state_location, country_location, part)

        # ltcf_df keys
        ltcf_age_bracket_keys = ['Under 65', '65–74', '75–84', '85 and over']
        facility_keys = [
                        # 'Hospice',
                        'Nursing home',
                        'Residential care community'
                        ]

        # state numbers
        facillity_users = {}
        for fk in facility_keys:
            facillity_users[fk] = {}
            facillity_users[fk]['Total'] = int(ltcf_df[ltcf_df.iloc[:, 0] == 'Number of users2, 5'][fk].values[0].replace(',', ''))
            for ab in ltcf_age_bracket_keys:
                facillity_users[fk][ab] = float(ltcf_df[ltcf_df.iloc[:, 0] == ab][fk].values[0].replace(',', ''))/100.

        total_facility_users = np.sum([facillity_users[fk]['Total'] for fk in facillity_users])

        # Census Bureau numbers 2016
        state_pop_2016 = 7288000
        state_age_distr_2016 = {}
        state_age_distr_2016['60-64'] = 6.3
        state_age_distr_2016['65-74'] = 9.0
        state_age_distr_2016['75-84'] = 4.0
        state_age_distr_2016['85-100'] = 1.8

        # Census Bureau numbers 2018
        state_pop_2018 = 7535591
        state_age_distr_2018 = {}
        state_age_distr_2018['60-64'] = 6.3
        state_age_distr_2018['65-74'] = 9.5
        state_age_distr_2018['75-84'] = 4.3
        state_age_distr_2018['85-100'] = 1.8

        for a in state_age_distr_2016:
            state_age_distr_2016[a] = state_age_distr_2016[a]/100.
            state_age_distr_2018[a] = state_age_distr_2018[a]/100.

        num_state_elderly_2016 = 0
        num_state_elderly_2018 = 0
        for a in state_age_distr_2016:
            num_state_elderly_2016 += state_pop_2016 * state_age_distr_2016[a]
            num_state_elderly_2018 += state_pop_2018 * state_age_distr_2018[a]

        expected_users_2018 = total_facility_users * num_state_elderly_2018/num_state_elderly_2016

        if verbose:
            print('number of elderly',num_state_elderly_2016, num_state_elderly_2018)
            print('growth in elderly', num_state_elderly_2018/num_state_elderly_2016)
            print('users in 2016',total_facility_users, '% of elderly', total_facility_users/num_state_elderly_2016)
            print('users in 2018', expected_users_2018)

        # location age distribution
        #age_brackets_16fp = os.path.join(datadir, 'demographics', 'contact_matrices_152_countries', country_location, state_location, 'age_distributions', 'Washington_census_age_brackets_16.dat')
        age_distr_16 = spdata.read_age_bracket_distr(datadir, country_location=country_location, state_location=state_location, location=location)
        age_brackets_16 = spdata.get_census_age_brackets(datadir, state_location=state_location, country_location=country_location,  nbrackets=16)
        age_by_brackets_dic_16 = spb.get_age_by_brackets_dic(age_brackets_16)

        # current King County population size
        pop = 2.25e6

        # local elderly population estimate
        local_elderly_2018 = 0
        #for ab in range(12, 16):
        for ab in range(12, spdata.get_nbrackets()):
            local_elderly_2018 += age_distr_16[ab] * pop

        if verbose:
            print('number of local elderly', local_elderly_2018)

        # growth_since_2016 = num_state_elderly_2018/num_state_elderly_2016
        # local_perc_elderly_2018 = local_elderly_2018/num_state_elderly_2018

        if verbose:
            print('local users in 2018?', total_facility_users * local_elderly_2018/num_state_elderly_2018 * num_state_elderly_2018/num_state_elderly_2016)
        # seattle_users_est_from_state = total_facility_users * local_perc_elderly_2018 * growth_since_2016

        est_seattle_users_2018 = dict.fromkeys(['60-64', '65-74', '75-84', '85-100'], 0)

        for fk in facillity_users:
            for ab in facillity_users[fk]:
                if ab != 'Total':
                    # print(fk, ab, facillity_users[fk][ab], facillity_users[fk][ab] * facillity_users[fk]['Total'], facillity_users[fk][ab] * facillity_users[fk]['Total'] * pop/state_pop_2018)
                    if ab == 'Under 65':
                        b = '60-64'
                    elif ab == '65–74':
                        b = '65-74'
                    elif ab == '75–84':
                        b = '75-84'
                    elif ab == '85 and over':
                        b = '85-100'
                    est_seattle_users_2018[b] += facillity_users[fk][ab] * facillity_users[fk]['Total'] * pop/state_pop_2018

        if verbose:
            for ab in est_seattle_users_2018:
                print(ab, est_seattle_users_2018[ab], est_seattle_users_2018[ab]/(state_age_distr_2018[ab] * pop))
            print(np.sum([est_seattle_users_2018[b] for b in est_seattle_users_2018]))

        # for pop of 2.25 million of Seattle
        est_ltcf_user_by_age_brackets_perc = {}
        for b in est_seattle_users_2018:
            est_ltcf_user_by_age_brackets_perc[b] = est_seattle_users_2018[b]/state_age_distr_2018[b]/pop
            # print(b,est_ltcf_user_by_age_brackets_perc[b])

        est_ltcf_user_by_age_brackets_perc['65-69'] = est_ltcf_user_by_age_brackets_perc['65-74']
        est_ltcf_user_by_age_brackets_perc['70-74'] = est_ltcf_user_by_age_brackets_perc['65-74']
        est_ltcf_user_by_age_brackets_perc['75-79'] = est_ltcf_user_by_age_brackets_perc['75-84']
        est_ltcf_user_by_age_brackets_perc['80-84'] = est_ltcf_user_by_age_brackets_perc['75-84']

        est_ltcf_user_by_age_brackets_perc.pop('65-74', None)
        est_ltcf_user_by_age_brackets_perc.pop('75-84', None)

        age_brackets_18_fp = os.path.join(spdata.get_relative_path(datadir),  country_location, state_location, 'age_distributions', f'{state_location}_age_bracket_distr_18.dat')

        age_distr_18 = spdata.read_age_bracket_distr(datadir, file_path=age_brackets_18_fp)

        age_brackets_18 = spdata.get_census_age_brackets(datadir, state_location, country_location, nbrackets=18)
        age_by_brackets_dic_18 = spb.get_age_by_brackets_dic(age_brackets_18)

        n = int(n)

        expected_users_by_age = {}

        for a in range(60, 101):
            if a < 65:
                b = age_by_brackets_dic_18[a]

                expected_users_by_age[a] = n * age_distr_18[b] / len(age_brackets_18[b])
                expected_users_by_age[a] = expected_users_by_age[a] * est_ltcf_user_by_age_brackets_perc['60-64']
                expected_users_by_age[a] = int(math.ceil(expected_users_by_age[a]))

            elif a < 75:
                b = age_by_brackets_dic_18[a]

                expected_users_by_age[a] = n * age_distr_18[b] / len(age_brackets_18[b])
                expected_users_by_age[a] = expected_users_by_age[a] * est_ltcf_user_by_age_brackets_perc['70-74']
                expected_users_by_age[a] = int(math.ceil(expected_users_by_age[a]))

            elif a < 85:
                b = age_by_brackets_dic_18[a]

                expected_users_by_age[a] = n * age_distr_18[b] / len(age_brackets_18[b])
                expected_users_by_age[a] = expected_users_by_age[a] * est_ltcf_user_by_age_brackets_perc['80-84']
                expected_users_by_age[a] = int(math.ceil(expected_users_by_age[a]))

            elif a < 101:
                b = age_by_brackets_dic_18[a]

                expected_users_by_age[a] = n * age_distr_18[b] / len(age_brackets_18[b])
                expected_users_by_age[a] = expected_users_by_age[a] * est_ltcf_user_by_age_brackets_perc['85-100']
                expected_users_by_age[a] = int(math.ceil(expected_users_by_age[a]))

        if verbose:
            print(np.sum([expected_users_by_age[a] for a in expected_users_by_age]))

        KC_resident_size_distr = spdata.get_usa_long_term_care_facility_residents_distr(datadir, location=location, state_location=state_location, country_location=country_location, use_default=use_default)
        KC_resident_size_distr = spb.norm_dic(KC_resident_size_distr)
        KC_residents_size_brackets = spdata.get_usa_long_term_care_facility_residents_distr_brackets(datadir, location=location, state_location=state_location, country_location=country_location, use_default=use_default)

        all_residents = []
        for a in expected_users_by_age:
            all_residents += [a] * expected_users_by_age[a]
        np.random.shuffle(all_residents)

        # place residents in facilities
        facilities = []

        size_bracket_keys = sorted([k for k in KC_resident_size_distr.keys()])
        size_distr_array = [KC_resident_size_distr[k] for k in size_bracket_keys]
        while len(all_residents) > 0:

            sb = np.random.choice(size_bracket_keys, p=size_distr_array)
            sb_range = KC_residents_size_brackets[sb]
            size = np.random.choice(sb_range)

            # size = int(np.random.choice(KC_ltcf_sizes))
            if size > len(all_residents):
                size = len(all_residents)

            new_facility = all_residents[0:size]
            facilities.append(new_facility)
            all_residents = all_residents[size:]

        max_age = 100

        expected_age_distr = dict.fromkeys(np.arange(max_age + 1), 0)
        expected_age_count = dict.fromkeys(np.arange(max_age + 1), 0)

        # adjust age distribution for those already created
        for a in expected_age_distr:
            expected_age_distr[a] = age_distr_16[age_by_brackets_dic_16[a]]/len(age_brackets_16[age_by_brackets_dic_16[a]])
            expected_age_count[a] = int(n * expected_age_distr[a])

        ltcf_adjusted_age_count = deepcopy(expected_age_count)
        for a in expected_users_by_age:
            ltcf_adjusted_age_count[a] -= expected_users_by_age[a]
        ltcf_adjusted_age_distr_dict = spb.norm_dic(ltcf_adjusted_age_count)
        ltcf_adjusted_age_distr = np.array([ltcf_adjusted_age_distr_dict[i] for i in range(max_age+1)])

        # exp_age_distr = np.array([expected_age_distr[i] for i in range(max_age+1)], dtype=np.float64)
        # exp_age_distr = np.array(list(expected_age_distr.values()), dtype=np.float64)

        # build rest of the population
        n_nonltcf = n - np.sum([len(f) for f in facilities])  # remove those placed in care homes


        # Move on
        household_size_distr = spdata.get_household_size_distr(datadir, location, state_location, country_location, use_default=use_default)
        hh_sizes = spcnx.generate_household_sizes_from_fixed_pop_size(n_nonltcf, household_size_distr)
        hha_brackets = spdata.get_head_age_brackets(datadir, country_location=country_location, state_location=state_location, use_default=use_default)
        hha_by_size = spdata.get_head_age_by_size_distr(datadir, country_location=country_location, state_location=state_location, use_default=use_default, household_size_1_included=cfg.default_household_size_1_included)

        contact_matrix_dic = spdata.get_contact_matrix_dic(datadir, sheet_name=sheet_name)

        homes_dic, homes = custom_generate_all_households(n_nonltcf, hh_sizes, hha_by_size, hha_brackets, age_brackets_16, age_by_brackets_dic_16, contact_matrix_dic, ltcf_adjusted_age_distr)
        homes = facilities + homes

        homes_by_uids, age_by_uid_dic = spcnx.assign_uids_by_homes(homes)  # include facilities to assign ids

        facilities_by_uids = homes_by_uids[0:len(facilities)]

        # Make a dictionary listing out uids of people by their age
        uids_by_age_dic = spb.get_ids_by_age_dic(age_by_uid_dic)

        # Generate school sizes
        school_sizes_count_by_brackets = spdata.get_school_size_distr_by_brackets(datadir, location=location, state_location=state_location, country_location=country_location, counts_available=school_enrollment_counts_available, use_default=use_default)
        school_size_brackets = spdata.get_school_size_brackets(datadir, location=location, state_location=state_location, country_location=country_location, use_default=use_default)

        # Figure out who's going to school as a student with enrollment rates (gets called inside sp.get_uids_in_school)
        uids_in_school, uids_in_school_by_age, ages_in_school_count = spcnx.get_uids_in_school(datadir, n_nonltcf, location, state_location, country_location, age_by_uid_dic, homes_by_uids, use_default=use_default)  # this will call in school enrollment rates

        if with_school_types:

            school_size_distr_by_type = spsm.get_default_school_size_distr_by_type()
            school_size_brackets = spsm.get_default_school_size_distr_brackets()

            school_types_by_age = spsm.get_default_school_types_by_age()
            school_type_age_ranges = spsm.get_default_school_type_age_ranges()

            syn_schools, syn_school_uids, syn_school_types = spcnx.send_students_to_school_with_school_types(school_size_distr_by_type, school_size_brackets, uids_in_school, uids_in_school_by_age,
                                                                                                             ages_in_school_count,
                                                                                                             school_types_by_age,
                                                                                                             school_type_age_ranges,
                                                                                                             verbose=verbose)
        else:
            # use contact matrices to send students to school

            # Get school sizes
            syn_school_sizes = spcnx.generate_school_sizes(school_sizes_count_by_brackets, school_size_brackets, uids_in_school)

            # Assign students to school
            syn_schools, syn_school_uids, syn_school_types = spcnx.send_students_to_school(syn_school_sizes, uids_in_school, uids_in_school_by_age, ages_in_school_count, age_brackets_16, age_by_brackets_dic_16, contact_matrix_dic, verbose)

        # Get employment rates
        employment_rates = spdata.get_employment_rates(datadir, location=location, state_location=state_location, country_location=country_location, use_default=use_default)

        # Find people who can be workers (removing everyone who is currently a student)
        potential_worker_uids, potential_worker_uids_by_age, potential_worker_ages_left_count = spcnx.get_uids_potential_workers(syn_school_uids, employment_rates, age_by_uid_dic)
        workers_by_age_to_assign_count = spcnx.get_workers_by_age_to_assign(employment_rates, potential_worker_ages_left_count, uids_by_age_dic)

        # Removing facilities residents from potential workers
        for nf, fc in enumerate(facilities_by_uids):
            for uid in fc:
                aindex = age_by_uid_dic[uid]
                if uid in potential_worker_uids:
                    potential_worker_uids_by_age[aindex].remove(uid)
                    potential_worker_uids.pop(uid, None)
                    if workers_by_age_to_assign_count[aindex] > 0:
                        workers_by_age_to_assign_count[aindex] -= 1

        # Assign teachers and update school lists
        syn_teachers, syn_teacher_uids, potential_worker_uids, potential_worker_uids_by_age, workers_by_age_to_assign_count = spcnx.assign_teachers_to_schools(syn_schools, syn_school_uids, employment_rates, workers_by_age_to_assign_count, potential_worker_uids, potential_worker_uids_by_age, potential_worker_ages_left_count,
                                                                                                                                                               average_student_teacher_ratio=average_student_teacher_ratio, teacher_age_min=teacher_age_min, teacher_age_max=teacher_age_max, verbose=verbose)

        syn_non_teaching_staff_uids, potential_worker_uids, potential_worker_uids_by_age, workers_by_age_to_assign_count = spcnx.assign_additional_staff_to_schools(syn_school_uids, syn_teacher_uids, workers_by_age_to_assign_count, potential_worker_uids, potential_worker_uids_by_age, potential_worker_ages_left_count,
                                                                                                                                                                    average_student_teacher_ratio=average_student_teacher_ratio, average_student_all_staff_ratio=average_student_all_staff_ratio, staff_age_min=staff_age_min, staff_age_max=staff_age_max, verbose=verbose)

        # Assign facilities care staff from 20 to 59

        datadir = datadir + ''
        KC_ratio_distr = spdata.get_usa_long_term_care_facility_resident_to_staff_ratios_distr(datadir, location=location, state_location=state_location, country_location=country_location, use_default=True)
        KC_ratio_distr = spb.norm_dic(KC_ratio_distr)
        KC_ratio_brackets = spdata.get_usa_long_term_care_facility_resident_to_staff_ratios_brackets(datadir, location=location, state_location=state_location, country_location=country_location, use_default=True)

        facilities_staff = []
        facilities_staff_uids = []

        sorted_ratio_keys = sorted([k for k in KC_ratio_distr.keys()])
        sorted_ratio_array = [KC_ratio_distr[k] for k in sorted_ratio_keys]

        staff_age_range = np.arange(ltcf_staff_age_min, ltcf_staff_age_max + 1)
        for nf, fc in enumerate(facilities):
            n_residents = len(fc)

            sb = np.random.choice(sorted_ratio_keys, p=sorted_ratio_array)
            sb_range = KC_ratio_brackets[sb]
            resident_staff_ratio = np.mean(sb_range)

            # if using raw staff totals in residents to staff ratios divide rato by 3 to split staff into 3 8 hour shifts at minimum
            resident_staff_ratio = resident_staff_ratio/3.
            # resident_staff_ratio = np.random.choice(KC_resident_staff_ratios)

            n_staff = int(math.ceil(n_residents/resident_staff_ratio))
            new_staff, new_staff_uids = [], []

            for i in range(n_staff):
                a_prob = np.array([workers_by_age_to_assign_count[a] for a in staff_age_range])
                a_prob = a_prob/np.sum(a_prob)
                aindex = np.random.choice(a=staff_age_range, p=a_prob)

                uid = potential_worker_uids_by_age[aindex][0]
                potential_worker_uids_by_age[aindex].remove(uid)
                potential_worker_uids.pop(uid, None)
                workers_by_age_to_assign_count[aindex] -= 1

                new_staff.append(aindex)
                new_staff_uids.append(uid)

            facilities_staff.append(new_staff)
            facilities_staff_uids.append(new_staff_uids)

        if verbose:
            print(len(facilities_staff_uids))
            for nf, fc in enumerate(facilities):
                print(fc, facilities_staff[nf], len(fc)/len(facilities_staff[nf]))

        # Generate non-school workplace sizes needed to send everyone to work
        workplace_size_brackets = spdata.get_workplace_size_brackets(datadir, state_location=state_location, country_location=country_location, use_default=use_default)
        workplace_size_distr_by_brackets = spdata.get_workplace_size_distr_by_brackets(datadir, state_location=state_location, country_location=country_location, use_default=use_default)
        workplace_sizes = spcnx.generate_workplace_sizes(workplace_size_distr_by_brackets, workplace_size_brackets, workers_by_age_to_assign_count)

        # Assign all workers who are not staff at schools to workplaces
        syn_workplaces, syn_workplace_uids, potential_worker_uids, potential_worker_uids_by_age, workers_by_age_to_assign_count = spcnx.assign_rest_of_workers(workplace_sizes, potential_worker_uids, potential_worker_uids_by_age, workers_by_age_to_assign_count, age_by_uid_dic, age_brackets_16, age_by_brackets_dic_16, contact_matrix_dic, verbose=verbose)

        # remove facilities from homes to write households as a separate file
        homes_by_uids = homes_by_uids[len(facilities_by_uids):]

        popdict = spcnx.make_contacts_from_microstructure_objects(age_by_uid_dic=age_by_uid_dic,
                                                                 homes_by_uids=homes_by_uids,
                                                                 schools_by_uids=syn_school_uids,
                                                                 teachers_by_uids=syn_teacher_uids,
                                                                 non_teaching_staff_uids=syn_non_teaching_staff_uids,
                                                                 workplaces_by_uids=syn_workplace_uids,
                                                                 facilities_by_uids=facilities_by_uids,
                                                                 facilities_staff_uids=facilities_staff_uids,
                                                                 use_two_group_reduction=use_two_group_reduction,
                                                                 average_LTCF_degree=average_LTCF_degree,
                                                                 with_school_types=with_school_types,
                                                                 school_mixing_type=school_mixing_type,
                                                                 average_class_size=average_class_size,
                                                                 inter_grade_mixing=inter_grade_mixing,
                                                                 average_student_teacher_ratio=average_student_teacher_ratio,
                                                                 average_teacher_teacher_degree=average_teacher_teacher_degree,
                                                                 average_student_all_staff_ratio=average_student_all_staff_ratio,
                                                                 average_additional_staff_degree=average_additional_staff_degree,
                                                                 trimmed_size_dic=trimmed_size_dic)

        return population


    def to_dict(self):
        ''' Export to a dictionary '''
        return sc.dcp(self.popdict)
