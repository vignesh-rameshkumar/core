import { useEffect, useState } from "react";
import { IconButton } from "@mui/material";
import { MdOutlineSupportAgent } from "react-icons/md";

const SupportButton = () => {
    const [showPopup, setShowPopup] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setShowPopup(false);
        }, 2000); // show initially 3s

        const interval = setInterval(() => {
            setShowPopup(true);
            setTimeout(() => {
                setShowPopup(false);
            }, 3000); // show for 3s every 3 min
        }, 180000); // 3 min break

        return () => {
            clearTimeout(timer);
            clearInterval(interval);
        };
    }, []);

    return (
        <div className="flex sm:hidden fixed bottom-20 right-6 z-50 flex flex-col items-end gap-2">
            {/* Popup */}
            <div
                className={`relative transition-all duration-500 ease-in-out 
                ${showPopup ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"}`}
            >
                <div className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm shadow-md relative">
                    Need Support?
                    {/* V Pointer */}
                    <div className="absolute -bottom-2 right-3 w-0 h-0 
                        border-l-8 border-r-8 border-t-8 
                        border-l-transparent border-r-transparent border-t-white">
                    </div>
                </div>
            </div>
            <a
                href="https://chat.google.com/room/AAAAXvY05KY"
                target="_blank"
                rel="noopener noreferrer"
            >
                {/* Floating Button */}
                <IconButton
                    className="!bg-gradient-to-r from-green-600 to-green-400 shadow-lg hover:scale-105 transition-transform duration-300"
                >
                    <MdOutlineSupportAgent className="text-white text-xl" />
                </IconButton>
            </a>
        </div>
    );
};

export default SupportButton;
