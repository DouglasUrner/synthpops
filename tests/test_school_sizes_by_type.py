"""
Test that school sizes are being generated by school type when with_school_types is turned on and data is available.
"""

import sciris as sc
import synthpops as sp
import numpy as np
import matplotlib as mplt
import matplotlib.pyplot as plt
import cmasher as cmr
import cmocean
import pytest
import settings

mplt.rcParams['font.family'] = 'Roboto Condensed'
mplt.rcParams['font.size'] = 7


# parameters to generate a test population
pars = sc.objdict(
    n                               = settings.pop_sizes.small_medium,
    rand_seed                       = 123,
    max_contacts                    = None,

    country_location                = 'usa',
    state_location                  = 'Washington',
    location                        = 'seattle_metro',
    use_default                     = True,

    with_facilities                 = 1,
    with_non_teaching_staff         = 1,
    with_school_types               = 1,

    school_mixing_type              = {'pk': 'age_and_class_clustered', 'es': 'age_and_class_clustered', 'ms': 'age_and_class_clustered', 'hs': 'random', 'uv': 'random'},  # you should know what school types you're working with
)


def test_school_types_created():
    """
    Test that unique school types are created.

    Returns:
        A list of the school types expected for the specified location.
    """
    sp.logger.info(f"Test that unique school types are created for each school.\nRun this first to see what school types you are working with.")
    test_pars = sc.dcp(pars)
    test_pars.n = settings.pop_sizes.small
    pop = sp.Pop(**pars)
    popdict = pop.to_dict()
    loc_pars = pop.loc_pars

    if pars['with_school_types']:
        expected_school_size_dist = sp.get_school_size_distr_by_type(**loc_pars)
        expected_school_types = sorted(expected_school_size_dist.keys())
    else:
        expected_school_types = [None]

    schools_by_type = dict()
    for i, person in popdict.items():
        if person['scid'] is not None:
            schools_by_type.setdefault(person['scid'], set())
            schools_by_type[person['scid']].add(person['sc_type'])

    for s, school_type in schools_by_type.items():
        assert len(school_type) == 1, f'Check failed. School {s} is listed as having more than one type.'
        schools_by_type[s] = list(school_type)[0]

    gen_school_types = sorted(set(schools_by_type.values()))
    assert gen_school_types == expected_school_types, f"Check failed. generated types: {gen_school_types}, expected: {expected_school_types}"

    print(f"School types generated for {pars['location']}: {set(schools_by_type.values())}")

    return list(set(schools_by_type.values()))


def test_plot_school_sizes(do_show=False, do_save=False):
    """
    Test that the school size distribution by type plotting method in sp.Pop
    class works.

    Visually show how the school size distribution generated compares to the
    data for the location being simulated.

    Notes:
        The larger the population size, the better the generated school size
        distributions by school type can match the expected data. If generated
        populations are too small, larger schools will be missed and in
        general there won't be enough schools generated to apply statistical
        tests.

    """
    sp.logger.info("Test that the school size distribution by type plotting method in sp.Pop class works. Note: For small population sizes, the expected and generated size distributions may not match very well given that the model is stochastic and demographics are based on much larger populations.")
    pop = sp.Pop(**pars)
    kwargs = sc.objdict(sc.mergedicts(pars, pop.loc_pars))
    kwargs.figname = f"test_school_size_distributions_{kwargs.location}_pop"
    kwargs.do_show = do_show
    kwargs.do_save = do_save
    kwargs.screen_height_factor = 0.20
    kwargs.hspace = 0.8
    kwargs.bottom = 0.09
    kwargs.keys_to_exclude = ['uv']
    kwargs.cmap = cmr.get_sub_cmap('cmo.curl', 0.08, 1)

    fig, ax = pop.plot_school_sizes(**kwargs)
    assert isinstance(fig, mplt.figure.Figure), 'Check 1 failed.'
    print('Check passed. Figure 1 made.')

    # works on popdict
    sp.logger.info("Test school size distribution plotting method on popdict.")
    popdict = pop.popdict
    kwargs.datadir = sp.datadir
    kwargs.do_show = False
    kwargs.figname = f"test_school_size_distributions_{kwargs.location}_popdict"
    fig2, ax2 = sp.plot_school_sizes(popdict, **kwargs)
    if not kwargs.do_show:
        plt.close()
    assert isinstance(fig2, mplt.figure.Figure), 'Check 2 failed.'
    print('Check passed. Figure 2 made.')

    sp.logger.info("Test school size distribution plotting method with keys_to_exclude as a string and without comparison.")
    kwargs.keys_to_exclude = 'uv'
    kwargs.comparison = False
    fig3, ax3 = pop.plot_school_sizes(**kwargs)
    assert isinstance(fig3, mplt.figure.Figure), 'Check 3 failed.'
    print('Check passed. Figure 3 made with keys_to_exclude as a string and without comparison.')

    return fig, ax, pop


def test_separate_school_types_for_seattle_metro(do_show=False, do_save=False):
    """
    Notes:
        By default, when no location is given and use_default is set to True,
        data pulled in will be for seattle metro and school type data will
        default to previous seattle metro data with pre-k and elementary kept
        separate.
    """
    sp.logger.info("Creating schools where pre-k and elementary schools are separate and school sizes are the same for all school types. Note: For small population sizes, the expected and generated size distributions may not match very well given that the model is stochastic and demographics are based on much larger populations.")
    test_pars = sc.dcp(pars)
    test_pars.location = None  # seattle_metro results with school size distribution the same for all types
    pop = sp.Pop(**test_pars)
    kwargs = sc.objdict(sc.dcp(test_pars))
    kwargs.do_show = do_show
    kwargs.do_save = do_save
    fig, ax = pop.plot_school_sizes(**kwargs)

    enrollment_by_school_type = pop.count_enrollment_by_school_type(**test_pars)
    school_types = enrollment_by_school_type.keys()

    assert ('pk' in school_types) and ('es' in school_types), 'Check failed. pk and es school type are not separately created.'
    print('Check passed.')

    return fig, ax, pop, school_types


def test_plot_schools_sizes_without_types(do_show=False, do_save=False):
    """Test that without school types, all schools are put together in one group."""
    sp.logger.info("Creating schools where school types are not specified. Test school size distribution plotting method without school types. Note: For small population sizes, the expected and generated size distributions may not match very well given that the model is stochastic and demographics are based on much larger populations.")
    pars.with_school_types = False  # need to rerun the population
    pop = sp.Pop(**pars)
    kwargs = sc.objdict(sc.mergedicts(pars, pop.loc_pars))
    kwargs.datadir = sp.datadir
    kwargs.do_show = do_show
    kwargs.do_save = do_save
    kwargs.screen_width_factor = 0.30
    kwargs.screen_height_factor = 0.20
    kwargs.width = 5
    kwargs.height = 3.2
    kwargs.figname = f"test_all_school_size_distributions_{kwargs.location}_pop"
    fig, ax = pop.plot_school_sizes(**kwargs)

    enrollment_by_school_type = pop.count_enrollment_by_school_type()
    school_types = list(enrollment_by_school_type.keys())

    assert school_types[0] is None and len(school_types) == 1, f"Check 3 failed. School types created: {school_types}."

    return fig, ax, pop


if __name__ == '__main__':

    # run as main to see the code and figures in action!
    sc.tic()

    school_types = test_school_types_created()
    fig0, ax0, pop0 = test_plot_school_sizes(do_show=True, do_save=True)
    fig1, ax1, pop1, school_types1 = test_separate_school_types_for_seattle_metro(do_show=True, do_save=True)
    fig2, ax2, pop2 = test_plot_schools_sizes_without_types(do_show=True, do_save=True)

    sc.toc()
