import apiRequest from "../api/apiRequest";
import dayjs from 'dayjs';
import { Tooltip, tooltipClasses, TooltipProps } from '@mui/material';
import { styled } from '@mui/material/styles';

export const getUserDetails = async () => {
    try {
        const response = await apiRequest(`/api/method/core.get_roles`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return {}
        }

    } catch (error) {
        console.error('Error getting data', error)
    }
}
export const getEmployeeActivity = async () => {
    try {
        const response = await apiRequest(`/api/method/payroll_management.api.attendance?request_type=self&from_date=${dayjs(new Date()).format('YYYY-MM-DD')}& to_date=${dayjs(new Date()).format('YYYY-MM-DD')}& page=1 & page_size=10`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message?.records[0]
            return transformedArray
        } else {
            return {}
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}


export const getModules = async () => {
    try {
        const response = await apiRequest(`/api/method/core.get_desk_data`, 'GET', '');
        if (response?.message) {
            const transformedArray = response?.message?.containers;
            return transformedArray
        } else {
            return []
        }
    }
    catch {
        console.error('Something went wrong!!!')
        return []
    }
}

export const CustomTooltip = styled(({ className, ...props }: TooltipProps) => (
    <Tooltip {...props} classes={{ popper: className }} />
))(() => ({
    [`& .${tooltipClasses.tooltip} `]: {
        backgroundColor: '#fff',
        color: '#181D27',
        boxShadow: '0px 2px 8px rgba(0,0,0,0.1)',
        fontSize: '12px',
        borderRadius: '6px',
        padding: '6px 10px',
    },
}));
