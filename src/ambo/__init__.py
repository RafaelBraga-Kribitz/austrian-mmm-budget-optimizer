"""Austrian MMM and Budget Optimizer.

A Bayesian marketing mix model (geometric adstock, Hill saturation, trend, yearly
seasonality, one control) with a budget optimiser on top. Three layers:

* Layer P: a synthetic advertiser with disclosed truth, used to prove the model
  recovers the parameters it was handed (``ambo.synth``, ``ambo.model``).
* Layer R: public demo data run through the same model (``ambo.data``).
* Layer D: the budget decision on the Layer R posterior (``ambo.optimize``).

``python -m ambo.run layer_p`` regenerates every Layer P artifact.
"""

__version__ = "0.1.0"
