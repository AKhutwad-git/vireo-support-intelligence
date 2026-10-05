"""Approximate normal confidence intervals for differences in independent means."""
from __future__ import annotations
from math import sqrt
from statistics import mean, stdev

def mean_interval(values: list[float], level_z: float=1.96, bounds: tuple[float,float] | None=None) -> dict:
    n=len(values)
    if n<2:
        return {"sample_size":n,"mean":mean(values) if n else None,"standard_error":None,"ci_lower":None,"ci_upper":None}
    avg=mean(values); se=stdev(values)/sqrt(n)
    lo,hi=avg-level_z*se,avg+level_z*se
    if bounds: lo=max(bounds[0],lo); hi=min(bounds[1],hi)
    return {"sample_size":n,"mean":avg,"standard_error":se,"ci_lower":lo,"ci_upper":hi}

def difference_interval(observed: list[float], expected: list[float], peer_sample_size: int, level_z: float=1.96,
                        gap_bounds: tuple[float,float] | None=None) -> dict:
    a=mean_interval(observed,level_z); b=mean_interval(expected,level_z)
    if not observed or not expected or a["standard_error"] is None or b["standard_error"] is None:
        return {"sample_size":len(observed),"peer_sample_size":peer_sample_size,"standard_error":None,"ci_lower":None,"ci_upper":None}
    se=sqrt(a["standard_error"]**2+b["standard_error"]**2)
    gap=a["mean"]-b["mean"]; lo,hi=gap-level_z*se,gap+level_z*se
    if gap_bounds:lo=max(gap_bounds[0],lo);hi=min(gap_bounds[1],hi)
    return {"sample_size":len(observed),"peer_sample_size":peer_sample_size,"standard_error":se,"ci_lower":lo,"ci_upper":hi}

def evidence_label(n: int) -> str:
    return "limited (<30 eligible observations)" if n<30 else "30+ eligible observations; uncertainty interval still applies"

def standardized_gap_interval(observed: list[float], peer_cells: list[list[float]], level_z: float=1.96,
                              gap_bounds: tuple[float,float] | None=None) -> dict:
    """SE for observed mean minus fixed-mix peer mean, using per-cell sampling variance."""
    n=min(len(observed),len(peer_cells))
    if n<2:
        return {"sample_size":n,"standard_error":None,"ci_lower":None,"ci_upper":None}
    obs=observed[:n]; cells=peer_cells[:n]
    obs_var=stdev(obs)**2/n
    expected_var=sum((stdev(cell)**2/len(cell) if len(cell)>1 else 0.0) for cell in cells)/(n*n)
    se=sqrt(obs_var+expected_var); gap=mean(obs)-sum(mean(c) for c in cells)/n
    lo,hi=gap-level_z*se,gap+level_z*se
    if gap_bounds:lo=max(gap_bounds[0],lo);hi=min(gap_bounds[1],hi)
    return {"sample_size":n,"standard_error":se,"ci_lower":lo,"ci_upper":hi}
