import axios, { AxiosRequestConfig } from 'axios';

let csrfToken: string | null = null;

const getCSRFToken = async (): Promise<string | null> => {
  if (csrfToken) return csrfToken;

  try {
    const response = await axios.get(`/api/method/core.api.csrf.token`, {
      withCredentials: true,
    });

    csrfToken = response?.data?.message?.csrf_token || null;
    localStorage.setItem('csrf_token', csrfToken || "");
    return csrfToken;
  } catch (error) {
    console.error("Failed to fetch CSRF token:", error);
    return null;
  }
};

const apiRequest = async <T>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body: T | null = null
): Promise<any> => {
  try {
    const token = await getCSRFToken();

    const options: AxiosRequestConfig = {
      method,
      url,
      data: body,
      withCredentials: true,  
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(token && { 'X-Frappe-CSRF-Token': token })
      },
    };

    const response = await axios(options);
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.exc_type === 'CSRFTokenError') {
      console.warn('Ignoring CSRFTokenError:', error.response.data);
      return null;
    }
    console.error('API request failed:', error);
    throw error;
  }
};

export default apiRequest;
