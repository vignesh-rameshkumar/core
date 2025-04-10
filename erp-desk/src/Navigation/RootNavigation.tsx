import { useEffect, useState } from "react";
import Desk from "../Pages/desk";
import { useDispatch } from "react-redux"
import { Routes, useNavigate, Route } from "react-router-dom";
import { getUserDetails } from "../Utils/helpers";
import { fetchUserData } from "../Store/Slices/userSlice";

const RootNavigation = () => {
    const navigate = useNavigate();
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
            setUserDetails(temp)
        }
        fetchUserData();
    }, [])

    useEffect(() => {
        if (!hasPermission) {
            navigate('/login')
        } else {
            navigate('/erp-desk')
        }
    }, [hasPermission])

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