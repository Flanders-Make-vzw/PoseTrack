import numpy as np
import cv2
import os
import json
import scipy
import sys
sys.path.append('/home/track/aic_cpp')
import aic_cpp

class Camera():
    def __init__(self,calib_data):

        self.project_mat = np.array(calib_data["camera projection matrix"])
        self.homo_mat = np.array(calib_data["homography matrix"])

        self.homo_inv = np.linalg.inv(self.homo_mat)
        self.project_inv = scipy.linalg.pinv(self.project_mat)
        
        # Calculate camera position using pseudo-inverse
        R = self.project_mat[:3, :3]  # Extract rotation matrix
        t = np.zeros(3)  # Initialize translation vector
        self.pos = -np.linalg.inv(R) @ t  # Calculate camera center

        self.homo_feet = self.homo_mat.copy()
        self.homo_feet[:, -1] = self.homo_feet[:, -1] + self.project_mat[:, 2] * 0.15  # z=0.15
        self.homo_feet_inv = np.linalg.inv(self.homo_feet)
        self.idx_int = calib_data["idx"]

    @staticmethod
    def from_colruyt_calib(calib_data):
        s = calib_data["intrinsics"]["camera_matrix"]["s"]
        w = calib_data["image_size"]["w"]
        h = calib_data["image_size"]["h"]
        processed_calib_data = {
            "camera projection matrix": [
                [s, 0, w / 2],
                [0, s, h / 2],
                [0, 0, 1]
            ],
            "homography matrix": [
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1]
            ],
            "idx": calib_data["camera_serial"]
        }
        camera = Camera(processed_calib_data)
        return camera

def cross(R,V):
    h = [R[1] * V[2] - R[2] * V[1],
         R[2] * V[0] - R[0] * V[2],
         R[0] * V[1] - R[1] * V[0]]
    return h

# def Point2LineDist(p_3d, pos, ray):
#     return np.linalg.norm(cross((p_3d-pos),ray))
def Point2LineDist(p_3d, pos, ray):
    return np.linalg.norm(np.cross(p_3d-pos,ray), axis=-1)

# def Point2LineDist(p_3d, ray_world_normalized):
#     #return np.linalg.norm(cross(p_3d,ray_world))
#     return np.dot(np.concatenate(p_3d,np.array([1])),ray_world_normalized)

# def Line2LineDist(rayA,rayB):
#     pA = np.array(-rayA[-1]/(rayA[0]+1e-10), 0, 0)
#     pB = np.array(-rayB[-1]/(rayB[0]+1e-10), 0, 0)

#     return Line2LineDist(pA, rayA[:-1], pB, rayB[:-1])


def Line2LineDist(pA, rayA, pB, rayB):
    if np.abs(np.dot(rayA, rayB)) > (1 - (1e-5))* np.linalg.norm(rayA, axis=-1) * np.linalg.norm(rayB, axis=-1):  #quasi vertical
        return Point2LineDist(pA, pB, rayA)
    else:
        rayCP =  np.cross(rayA,rayB)
        return np.abs((pA-pB).dot(rayCP / np.linalg.norm(rayCP,axis=-1), axis=-1))

def Line2LineDist_norm(pA, rayA, pB, rayB):
    rayCP = np.cross(rayA, rayB, axis=-1)
    rayCP_norm = np.linalg.norm(rayCP, axis=-1) + 1e-6
    return np.abs(np.sum((pA-pB) * (rayCP / rayCP_norm[:, None]), -1))
    return np.where(
        rayCP_norm < 1e-5,
        Point2LineDist(pA, pB, rayA),
        np.abs(np.sum((pA-pB) * (rayCP / rayCP_norm[:, None]), -1))
    )
    if np.abs(np.dot(rayA, rayB)) > (1 - (1e-5)):  #quasi parallel
        return Point2LineDist(pA, pB, rayA)
    else:
        rayCP = np.cross(rayA,rayB, axis=-1)
        return np.abs(np.sum((pA-pB) * (rayCP / np.linalg.norm(rayCP,axis=-1)), -1))
    
def epipolar_3d_score(pA, rayA, pB, rayB, alpha_epi):
    dist = Line2LineDist(pA, rayA, pB, rayB)
    return 1- dist/alpha_epi

def epipolar_3d_score_norm(pA, rayA, pB, rayB, alpha_epi):
    dist = Line2LineDist_norm(pA, rayA, pB, rayB)
    return 1- dist/alpha_epi

# import aic_cpp
# print(dir(aic_cpp))

epipolar_3d_score_norm = aic_cpp.epipolar_3d_score_norm

# def epipolar_3d_score(rayA, rayB, alpha_epi):
#     dist = Line2LineDist(rayA, rayB)
#     return 1- dist/alpha_epi