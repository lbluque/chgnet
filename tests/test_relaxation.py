from __future__ import annotations

import re
from typing import Literal

import pytest
import torch
from pymatgen.core import Structure
from pytest import approx, mark, param

from chgnet import ROOT
from chgnet.graph import CrystalGraphConverter
from chgnet.model import CHGNet, StructOptimizer

structure = Structure.from_file(f"{ROOT}/examples/mp-18767-LiMnO2.cif")


@pytest.mark.parametrize("algorithm", ["legacy", "fast"])
def test_relaxation(algorithm: Literal["legacy", "fast"]):
    chgnet = CHGNet.load()
    converter = CrystalGraphConverter(
        atom_graph_cutoff=5, bond_graph_cutoff=3, algorithm=algorithm
    )
    assert converter.algorithm == algorithm

    chgnet.graph_converter = converter
    relaxer = StructOptimizer(model=chgnet)
    result = relaxer.relax(structure, verbose=True)
    assert list(result) == ["final_structure", "trajectory"]

    traj = result["trajectory"]
    # make sure trajectory has expected attributes
    assert {*traj.__dict__} == {
        *"atoms energies forces stresses magmoms atom_positions cells".split()
    }
    assert len(traj) == 4

    # make sure final structure is more relaxed than initial one
    assert traj.energies[0] > traj.energies[-1]
    assert traj.energies[-1] == approx(-58.972927)


no_cuda = mark.skipif(not torch.cuda.is_available(), reason="No CUDA device")
no_mps = mark.skipif(not torch.backends.mps.is_available(), reason="No MPS device")


@mark.parametrize(
    "use_device", ["cpu", param("cuda", marks=no_cuda), param("mps", marks=no_mps)]
)
def test_structure_optimizer_passes_kwargs_to_model(use_device) -> None:
    relaxer = StructOptimizer(use_device=use_device)
    assert re.match(rf"{use_device}(:\d+)?", relaxer.calculator.device)
