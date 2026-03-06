"""Least squares regression analysis."""

# import needed modules
import logging
import numpy as np

_logger = logging.getLogger(__name__)



def generateA(var1_arr, var2_arr, var3_arr, var4_arr, var5_arr):
    """Build a design matrix A by column-stacking input arrays (template/example)."""
    A = np.column_stack((
        var1_arr,
        var2_arr,
        var3_arr,
        var4_arr,
        var5_arr,
        var5_arr * var3_arr,
    ))
    A_np = np.array(A)
    return A_np


def generate_residual(calculated, truth):
    """Compute residual (calculated - truth) and its Euclidean norm.

    Written by Anders Bandt, August 2021.

    Returns:
        [residual, euclidean_norm]
    """
    residual = (calculated - truth)  # compute residual
    euclidean_norm = np.linalg.norm(residual)
    # min_res = min(residual)
    # max_res = max(residual)  # get residual statistics
    # fullscale_error = (max_res - min_res) * max(inputs) / 100  # compute full scale error
    # print(f"Fullscale error: {fullscale_error} %")

    # scale residual
    # scaled_res = datah.scale_array(residual, -1, 1)

    return [residual, euclidean_norm]


def least_squares(A, d):
    """Solve the least-squares problem Aw = d via numpy.linalg.lstsq.

    Written by Anders Bandt, August 2021.

    Args:
        A: Design matrix (m x n).
        d: Observation vector (m x 1).

    Returns:
        w: Coefficient vector (n x 1).
    """
    # Create matrices and find w from data
    # w = np.linalg.inv(A.transpose() @ A) @ A.transpose() @ d

    w, residuals, rank, s = np.linalg.lstsq(A.astype(np.float64), d.astype(np.float64), rcond=None)

    return w


##############################
######### ECE 532    #########
##############################

def ista_solve_hot(A, d, la_array):
    """Iterative soft-thresholding (ISTA) with hot start for LASSO regression.

    Solves: minimize |Ax - d|_2^2 + lambda * |x|_1
    Uses the converged solution for each lambda as the initial condition for the next.
    """
    max_iter = 10 ** 4
    tol = 10 ** (-3)
    tau = 1 / np.linalg.norm(A, 2) ** 2
    n = A.shape[1]
    w = np.zeros((n, 1))
    num_lam = len(la_array)
    X = np.zeros((n, num_lam))
    for i, each_lambda in enumerate(la_array):
        for j in range(max_iter):
            z = w - tau * (A.T @ (A @ w - d))
            w_old = w
            w = np.sign(z) * np.clip(np.abs(z) - tau * each_lambda / 2, 0, np.inf)
            X[:, i:i + 1] = w
            if np.linalg.norm(w - w_old) < tol:
                break
    return X


def prxgraddescent_l2(A, d, la_array):
    """L2-regularized proximal gradient descent: w_{k+1} = (w_k - tau*A'*(A*w_k - d)) / (1 + lam*tau)."""
    max_iter = 10 ** 4
    tol = 10 ** (-3)
    tau = 1 / np.linalg.norm(A, 2) ** 2
    n = A.shape[1]
    w = np.zeros((n, 1))
    num_lam = len(la_array)
    X = np.zeros((n, num_lam))
    #W = np.zeros((w_init.shape[0], it+1))
    #Z = np.zeros((w_init.shape[0], it+1))
    for i, each_lambda in enumerate(la_array):
        #W[:,[0]] = w_init
        for j in range(max_iter):
            z = w - tau * A.T @ (A @ w - d);
            w_old = w
            w = z / (1 + each_lambda * tau)
            X[:, i:i + 1] = w
            if np.linalg.norm(w - w_old) < tol:
                break
    return X


def run_prxgd(A, d):
    """Run ISTA/LASSO solver with a default lambda schedule."""
    lambdas = np.logspace(-6, 20, num=25)
    lambdas = [1]
    w = ista_solve_hot(A, d, lambdas)
    _logger.debug(f"The dimensions of the output weight vectors are: {np.shape(w)}")
    return w
