import { useFrappeGetDoc } from "frappe-react-sdk";
import { useState } from "react";
import Desk from "../Pages/desk";
import apiRequest from "../api/apiRequest";

const RootNavigation = () => {
    const [userDetails, setUserDetails] = useState<any>({
        userRoles: [],
        department: "",
    });
    const [darkMode, setDarkMode] = useState(false);
    const cookiesArray = document.cookie.split("; ");
    const cookieData: { [key: string]: string } = {};
    cookiesArray.forEach((cookie) => {
        const [key, value] = cookie.split("=");
        cookieData[key.trim()] = decodeURIComponent(value);
    });
    const hasPermission = ["Employee"].some((role) => userDetails?.userRoles.includes(role));
    const getUserDetails = async () => {
        try {
            const response = await apiRequest(`/api/method/manufacturing.agnikul_manufacturing.get_api.get_users_role`, "GET", "")
            if (response?.message) {
                let tempRoles = response?.message?.roles;
                let tempDept = response?.message?.department;
                let funcDept = response?.message?.func_dept;
                setUserDetails({ userRoles: tempRoles, department: tempDept, functionDepartment: funcDept });
            }

        } catch (error) {
            console.error('Error getting data', error)
        }
    }
    return (
        <div><Desk /></div>
    )
}

export default RootNavigation