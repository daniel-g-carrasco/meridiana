//! The battery dispatch of Meridiana's `economics.dispatch`, hour by hour, as a Rust extension built with
//! PyO3 and maturin: a measurement for register R31 (study 18, theme C), not a feature of the program.
//!
//! The loop is the Python one, line for line: charge with the surplus within the charge power and the room
//! left, discharge on the shortfall within the discharge power and the energy held; the round-trip efficiency
//! split half on the way in (eta = sqrt(efficiency)) and half on the way out.

use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// (stored, given, soc) for every hour: kWh into the battery from the system, kWh from the battery to the
/// loads, the state of charge at the end of the hour.
#[pyfunction]
fn dispatch<'py>(
    py: Python<'py>,
    prod: PyReadonlyArray1<'py, f64>,
    cons: PyReadonlyArray1<'py, f64>,
    usable_kwh: f64,
    charge_kw: f64,
    discharge_kw: f64,
    efficiency: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>)> {
    let prod = prod.as_slice()?;
    let cons = cons.as_slice()?;
    if prod.len() != cons.len() {
        return Err(PyValueError::new_err("prod and cons must have the same length"));
    }
    let n = prod.len();
    let eta = efficiency.sqrt();
    let mut stored = vec![0.0f64; n];
    let mut given = vec![0.0f64; n];
    let mut soc = vec![0.0f64; n];
    let mut level = 0.0f64;
    for h in 0..n {
        let x = prod[h] - cons[h];
        if x > 0.0 {
            let room = (usable_kwh - level) / eta;
            let c = x.min(charge_kw).min(room);
            stored[h] = c;
            level += c * eta;
        } else if x < 0.0 {
            let d = (-x).min(discharge_kw).min(level * eta);
            given[h] = d;
            level -= d / eta;
        }
        soc[h] = level;
    }
    Ok((stored.into_pyarray(py), given.into_pyarray(py), soc.into_pyarray(py)))
}

#[pymodule]
fn dispatch_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dispatch, m)?)?;
    Ok(())
}
