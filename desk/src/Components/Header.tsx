// import { useState } from "react";
import { useMediaQuery, InputBase } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import logoMini from "../Assets/agnikul.png";
import logo from "../Assets/LogoAgnikul.png";
import profilePic from "../Assets/background.png";
// import { IoMdHome } from "react-icons/io";
// import { BsFillGridFill, BsPersonCheckFill, BsFillPersonLinesFill } from "react-icons/bs";

const Header = () => {
    const isMobile = useMediaQuery("(max-width:600px)");
    // const [activeMenu, setActiveMenu] = useState("Home");

    // const menuItems = [
    //     { name: "Home", icon: <IoMdHome size={18} /> },
    //     { name: "Dashboard", icon: <BsFillGridFill size={16} /> },
    //     { name: "Request Approval", icon: <BsPersonCheckFill size={16} /> },
    //     { name: "Assignments", icon: <BsFillPersonLinesFill size={16} /> },
    // ];

    return (
        <div className="bg-[#FFF] h-[10%] fixed top-0 w-full flex justify-between items-center px-4 sm:px-15 shadow-md z-50">
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
                <div className="relative flex items-center border border-gray-300 rounded-lg px-2 sm:px-3 w-[60%]">
                    <SearchIcon className="text-gray-500" />
                    <InputBase
                        placeholder="Search"
                        className="ml-2 outline-none bg-transparent w-full text-gray-700 placeholder-gray-500"
                    />
                </div>
                <img
                    src={profilePic}
                    alt="Profile"
                    className="w-8 h-8 rounded-full border cursor-pointer"
                />
            </div>
        </div>
    );
};

export default Header;
