import { useEffect, useState } from "react";
import Desk from "../Pages/desk";
import { useDispatch } from "react-redux"
import { Routes, Route } from "react-router-dom";
import { getUserDetails } from "../Utils/helpers";
import { fetchUserData } from "../Store/Slices/userSlice";

const RootNavigation = () => {
    const dispatch = useDispatch();
    const [userDetails, setUserDetails] = useState<any>({});
    const cookiesArray = document.cookie.split("; ");
    const cookieData: { [key: string]: string } = {};
    cookiesArray.forEach((cookie) => {
        const [key, value] = cookie.split("=");
        cookieData[key.trim()] = decodeURIComponent(value);
    });
    const hasPermission = userDetails?.roles?.includes('Employee')


    useEffect(() => {
        const fetchUserData = async () => {
            const temp = await getUserDetails();
            if (temp?.roles?.includes('Employee')) {
                if (window.location.pathname !== '/erp-desk') {
                    window.location.href = '/erp-desk';
                }
            } else {
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login'; 
                }
            }
            setUserDetails(temp);
        };
        fetchUserData();
    }, []);
    

    useEffect(() => {
        dispatch(fetchUserData());
    }, [dispatch]);
    return (
        <div>{hasPermission &&
            <Routes>
                <Route
                    path="/erp-desk"
                    element={
                        <Desk />}
                />
            </Routes>}</div>
    )
}

export default RootNavigation