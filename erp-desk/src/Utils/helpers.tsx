import apiRequest from "../api/apiRequest";
import dayjs from 'dayjs';

export const getEmployeeDetails = async () => {
    try {
        const response = await apiRequest(`/api/method/payroll_management.api.attendance?request_type=self&from_date=${dayjs(new Date()).format("YYYY-MM-DD")}&to_date=${dayjs(new Date()).format("YYYY-MM-DD")}&page=1&page_size=10`, 'GET', '');
        if (response?.message) {
            const transformedArray = response?.message?.records[0]
            return transformedArray
        } else {
            return {}
        }
    }
    catch {
        console.error('Something went wrong!!!')
        return {}
    }
}