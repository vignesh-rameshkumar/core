// import { useState } from "react";
import { useMediaQuery, InputBase, CircularProgress, IconButton } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import logoMini from "../Assets/agnikul.png";
import logo from "../Assets/LogoAgnikul.png";
import { useSelector } from 'react-redux';
import profilePic from "../Assets/profile-vector.jpg";
import { RootState } from "../Store";
import { useEffect, useRef, useState } from "react";
import { clearCacheData, handleNavigateSearch } from "../Utils/helpers";
import apiRequest from "../api/apiRequest";
import { IoIosClose } from "react-icons/io";
import { useFrappeAuth } from "frappe-react-sdk";

// import { IoMdHome } from "react-icons/io";
// import { BsFillGridFill, BsPersonCheckFill, BsFillPersonLinesFill } from "react-icons/bs";

const Header = () => {
    const isMobile = useMediaQuery("(max-width:600px)");
    const userData = useSelector((state: RootState) => state.user.data);
    const [open, setOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [loading, setLoading] = useState(false);
    const [searchData, setSearchData] = useState([]);
    const [searchText, setSearchText] = useState("");
    const debounceRef = useRef<NodeJS.Timeout | null>(null);
    const { logout } = useFrappeAuth();
    const handleLogout = () => {
        logout();
        setTimeout(() => {
            window.location.href = "/login";
        }, 1000);
    };
    const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
        const query = e.target.value;
        setSearchText(query);

        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            fetchEmployees(query);
        }, 500);
    };

    const fetchEmployees = async (query: string) => {
        setLoading(true);
        let filter = query ? `txt=${query}&limit=1000` : "";
        try {
            const response = await apiRequest(`api/method/core.search?${filter}`, "GET", "");
            if (response?.message) {
                setSearchData(response.message);
            }
        } catch (error) {
            console.error("Error getting data", error);
        } finally {
            setLoading(false);
        }
    };
    // Close when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: any) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);
    // const [activeMenu, setActiveMenu] = useState("Home");

    // const menuItems = [
    //     { name: "Home", icon: <IoMdHome size={18} /> },
    //     { name: "Dashboard", icon: <BsFillGridFill size={16} /> },
    //     { name: "Request Approval", icon: <BsPersonCheckFill size={16} /> },
    //     { name: "Assignments", icon: <BsFillPersonLinesFill size={16} /> },
    // ];


    return (
        <div className="bg-[#FFF] z-999 h-[8%] w-full flex justify-between items-center px-4 sm:px-15 shadow-md z-50">
            <img
                src={isMobile ? logoMini : logo}
                alt="Logo"
                className="w-[7%] sm:w-[13%]"
            />

            {/* Desktop Menu */}
            {/* <div className="hidden sm:flex gap-4 bg-[#F5F5F5] p-2 border-[1px] border-[#E9EAEB] rounded-[5px]">
                {menuItems.map((item) => (
                    <button
                        key={item.name}
                        onClick={() => setActiveMenu(item.name)}
                        className={`flex items-center gap-2 px-3 py-1 rounded-md text-sm transition-all duration-200 cursor-pointer  hover:bg-[#00984B9C]
                            ${activeMenu === item.name
                                ? "bg-[#4D8C52] text-white"
                                : "bg-[#F3F3F3] text-black"
                            }`}
                    >
                        {item.icon}
                        {item.name}
                    </button>
                ))}
            </div> */}

            {/* Search & Profile */}
            <div className="flex items-center gap-4 w-[80%] sm:w-[40%] justify-end">
                <div className="relative flex flex-col w-[60%]">
                    <div className="flex items-center border border-gray-300 rounded-lg pl-2 sm:pl-3">
                        <SearchIcon className="text-gray-500" />
                        <InputBase
                            onChange={handleSearch}
                            value={searchText}
                            placeholder="Search"
                            className="ml-2 outline-none bg-transparent w-full text-gray-700 placeholder-gray-500"
                        />
                        {loading ? <div className="text-center pt-1 pr-3"> <CircularProgress size={15} className=" !text-[#4D8C52]" /></div> : searchText && <IconButton onClick={() => setSearchText('')} className="rounded-full"><IoIosClose className="!text-gray-500 text-xl" /></IconButton>
                        }
                    </div>

                    {searchText && searchData.length > 0 && (
                        <div className="absolute top-[105%] left-0 right-0 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto z-10">
                            {searchData.map((item: any, index: number) => (
                                <div
                                    key={index}
                                    onClick={() => handleNavigateSearch(item.name)}
                                    className="px-4 py-2 cursor-pointer hover:bg-gray-100 text-sm text-gray-700"
                                >
                                    {item.name}
                                </div>
                            ))}
                        </div>
                    )}

                    {searchText && !loading && searchData.length === 0 && (
                        <div className="absolute top-[105%] left-0 right-0 bg-white border border-gray-300 rounded-lg shadow-lg z-10 px-4 py-2 text-sm text-gray-500">
                            No results found
                        </div>
                    )}
                </div>
                <div className="relative" ref={dropdownRef}>
                    <img
                        onClick={() => setOpen(!open)}
                        src={userData?.user_image || profilePic}
                        alt="Profile"
                        className="w-10 h-10 rounded-full border cursor-pointer"
                    />

                    {open && (
                        <div className="absolute right-0 mt-2 w-40 bg-white shadow-lg rounded-md border z-50">
                            <div
                                onClick={() => { window.location.href = '/app/user-profile' }}
                                className="px-4 py-2 text-[#222] hover:bg-gray-100 cursor-pointer"
                            >
                                My Profile
                            </div>
                            <div
                                onClick={() => { clearCacheData() }}
                                className="px-4 py-2 text-[#222] hover:bg-gray-100 cursor-pointer"
                            >
                                Reload
                            </div>
                            <div
                                onClick={() => { handleLogout() }}
                                className="px-4 py-2 text-[#222] hover:bg-gray-100 cursor-pointer "
                            >
                                Logout
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Header;
