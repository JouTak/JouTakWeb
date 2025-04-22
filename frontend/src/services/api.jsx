import axios from "axios";

export const API_BASE_URL = "__REACT_APP_API_URL__";

/* ============================================================
   Аутентификация & Общие настройки
============================================================ */

export const obtainToken = (username, password) => {
    return axios.post(`${API_BASE_URL}token/`, {username, password});
};

export const refreshToken = (refreshToken) => {
    return axios.post(`${API_BASE_URL}token/refresh/`, {refresh: refreshToken});
};

export const setupAxiosInterceptors = (logout) => {
    axios.interceptors.response.use(
        (response) => response,
        (error) => {
            if (error.response && error.response.status === 401) {
                logout();
                window.location.href = "/login";
            }
            return Promise.reject(error);
        },
    );
};

export const setAuthToken = (token) => {
    if (token) {
        axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
        delete axios.defaults.headers.common["Authorization"];
    }
};


export const getUserProfile = () => axios.get(`${API_BASE_URL}user/profile/`);
export const updateProfilePicture = (data) =>
    axios.post(`${API_BASE_URL}/user/profile/upload_avatar/`, data);
export const updateUserSettings = (data) =>
    axios.put(`${API_BASE_URL}user/settings/`, data);