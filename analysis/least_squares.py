
# import needed modules
import numpy as np
from scipy.io import loadmat
import matplotlib.pyplot as plt
from pprint import pprint
import pandas as pd

# import user defined modules
from data import data_helper as datah



def generateA(var1_arr, var2_arr):
    A = np.column_stack((
        # var1_arr ** 2,
        var1_arr,
        # np.sqrt(var1_arr),
        # var2_arr ** 2,
        # var2_arr,
        np.ones_like(var1_arr)
    ))
    # A_float = np.vectorize(datah.convert_to_float)(A)
    # A_float = np.array([[datah.convert_to_float(val) for val in row] for row in A])
    # A = A_float[~np.isnan(A_float).any(axis=1)] # removes nan values but leaves mismatch with truth values
    A_np = np.array(A)
    return A_np


# GenerateResidual: Generates a residual along with some statistics
# @param[out] residual: calculated as (calculated - true)
# @param[out] euclidean_norm: Euclidean (or '2') norm of the residual
# @param[out] fullscale_error: Full scale error
# Written by Anders Bandt, August 2021
def generate_residual(calculated, truth):
    residual = (calculated - truth)  # compute residual
    euclidean_norm = np.linalg.norm(residual)
    # min_res = min(residual)
    # max_res = max(residual)  # get residual statistics
    # fullscale_error = (max_res - min_res) * max(inputs) / 100  # compute full scale error
    # print(f"Fullscale error: {fullscale_error} %")
    # TODO: add a dictionary to track stats

    # scale residual
    # scaled_res = datah.scale_array(residual, -1, 1)

    return [residual, euclidean_norm]


#LeastSquares: Compute Least Squares Matrix Regression
#       This function computes the least squares regression of Aw=d where
# A = matrix of input values according to predefined equation
# d = input truth values to train with
# @param[out]     w          output vector of coefficients
# @param[out]     y          new calculated truth pressures with w
# @param[out]     residual   difference between y - d (calculated truth vs input truth)
# Written by Anders Bandt, August 2021
def least_squares(A, d):
    # Create matrices and find w from data
    w = np.linalg.inv(A.transpose() @ A) @ A.transpose() @ d

    return w


##############################
######### ECE 532    #########
##############################

# ista_solve_hot: Iterative soft-thresholding for multiple values of
# lambda with hot start for each case - the converged value for the previous
# value of lambda is used as an initial condition for the current lambda.
# this function solves the minimization problem
# Minimize |Ax-d|_2^2 + lambda*|x|_1 (Lasso regression)
# using iterative soft-thresholding.
def ista_solve_hot(A, d, la_array):
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


## compute it iterations of L2 proximal gradient descent starting at w1
## w_{k+1}= (w_k - tau*X'*(X*w_k - y)/(1+lam*tau)
## step size tau
def prxgraddescent_l2(A, d, la_array):
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


# implements soft iterative thresholding via proximal gradient descent to solve the LASSO problem
def run_prxgd(A, d):
    lambdas = np.logspace(-6, 20, num=25)
    lambdas = [1]
    w = ista_solve_hot(A, d, lambdas)
    print("The dimensions of the output weight vectors are...")
    print(np.shape(w))
    return w
