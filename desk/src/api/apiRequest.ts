import axios, { AxiosRequestConfig } from 'axios';


const apiRequest = async <T>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body: T | null = null
): Promise<any> => {
  try {

    const options: AxiosRequestConfig = {
      method,
      url,
      data: body,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    };
    const response = await axios(options);
    return response.data; 
  } catch (error: any) {
    // Handle CSRFTokenError gracefully
    if (error.response?.data?.exc_type === 'CSRFTokenError') {
      console.warn('Ignoring CSRFTokenError:', error.response.data);
      return null; 
    }
    
    console.error('API request failed:', error);
    throw error; 
  }
};

export default apiRequest;
