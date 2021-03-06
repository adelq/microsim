from microsim.outcome import OutcomeType
from microsim.outcome_model_type import OutcomeModelType
from microsim.outcome import Outcome
from microsim.statsmodel_linear_risk_factor_model import StatsModelLinearRiskFactorModel
from microsim.regression_model import RegressionModel
from microsim.data_loader import load_model_spec


import numpy.random as npRand
import scipy.special as scipySpecial


class CVOutcomeDetermination:
    default_mi_case_fatality = 0.13
    default_secondary_mi_case_fatality = 0.13
    default_stroke_case_fatality = 0.15
    default_secondary_stroke_case_fatality = 0.15
    default_secondary_prevention_multiplier = 1.0

    # fatal stroke probability estimated from our meta-analysis of BASIC, NoMAS, GCNKSS, REGARDS
    # fatal mi probability from: Wadhera, R. K., Joynt Maddox, K. E., Wang, Y., Shen, C., Bhatt,
    # D. L., & Yeh, R. W.
    # (2018). Association Between 30-Day Episode Payments and Acute Myocardial Infarction Outcomes
    # Among Medicare
    # Beneficiaries. Circ. Cardiovasc. Qual. Outcomes, 11(3), e46–9.
    # http://doi.org/10.1161/CIRCOUTCOMES.117.004397

    def __init__(self,
                 mi_case_fatality=default_mi_case_fatality,
                 stroke_case_fatality=default_stroke_case_fatality,
                 mi_secondary_case_fatality=default_secondary_mi_case_fatality,
                 stroke_secondary_case_fatality=default_secondary_stroke_case_fatality,
                 secondary_prevention_multiplier=default_secondary_prevention_multiplier):
        self.mi_case_fatality = mi_case_fatality
        self.mi_secondary_case_fatality = mi_secondary_case_fatality,
        self.stroke_case_fatality = stroke_case_fatality
        self.stroke_secondary_case_fatality = stroke_secondary_case_fatality
        self.secondary_prevention_multiplier = secondary_prevention_multiplier

    def _will_have_cvd_event(self, ascvdProb):
        return npRand.uniform(size=1) < ascvdProb

    def _will_have_mi(self, person, outcome_model_repository, manualMIProb=None):
        if manualMIProb is not None:
            return npRand.uniform(size=1) < manualMIProb
        # if no manual MI probablity, estimate it from oru partitioned model
        strokeProbability = self.get_stroke_probability(person)

        return npRand.uniform(size=1) < (1 - strokeProbability)

    def get_stroke_probability(self, person):
        model_spec = load_model_spec("StrokeMIPartitionModel")
        strokePartitionModel = StatsModelLinearRiskFactorModel(RegressionModel(**model_spec))
        strokeProbability = scipySpecial.expit(strokePartitionModel.estimate_next_risk(person))
        return strokeProbability

    def _will_have_fatal_mi(self, person, overrideMIProb=None):
        fatalMIProb = overrideMIProb if overrideMIProb is not None else self.mi_case_fatality
        fatalProb = self.mi_secondary_case_fatality if person._mi else fatalMIProb
        return npRand.uniform(size=1) < fatalProb

    def _will_have_fatal_stroke(self, person, overrideStrokeProb=None):
        fatalStrokeProb = overrideStrokeProb if overrideStrokeProb is not None else self.stroke_case_fatality
        fatalProb = self.stroke_secondary_case_fatality if person._stroke else fatalStrokeProb
        return npRand.uniform(size=1) < fatalProb

    def assign_outcome_for_person(
            self,
            outcome_model_repository,
            person,
            years=1,
            manualStrokeMIProbability=None):

        cvRisk = outcome_model_repository.get_risk_for_person(person,
                                                              OutcomeModelType.CARDIOVASCULAR,
                                                              years=1)

        if person._stroke or person._mi:
            cvRisk = cvRisk * self.secondary_prevention_multiplier

        if self._will_have_cvd_event(cvRisk):
            if self._will_have_mi(person, outcome_model_repository, manualStrokeMIProbability):
                if self._will_have_fatal_mi(person):
                    return Outcome(OutcomeType.MI, True)
                else:
                    return Outcome(OutcomeType.MI, False)
            else:
                if self._will_have_fatal_stroke(person):
                    return Outcome(OutcomeType.STROKE, True)
                else:
                    return Outcome(OutcomeType.STROKE, False)
