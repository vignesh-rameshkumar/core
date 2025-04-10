// import { IconButton } from '@mui/material';
import automation from '../Assets/automation.png'
// import { IoMdHome } from "react-icons/io";
// import { BsFillGridFill } from "react-icons/bs";
// import { BsPersonCheckFill } from "react-icons/bs";
// import { BsFillPersonLinesFill } from "react-icons/bs";
// import { MdOutlineSupportAgent } from "react-icons/md";
import SupportPopup from './SupportBtn';



const Footer = () => {

    return (
        <div className="bg-[#FFF] fixed bottom-0 h-[7%] w-full flex flex-col sm:flex-row justify-between items-center px-4 sm:px-15 shadow-md">
            <div className="flex items-center mt-3 sm:mt-0">
                <p className="text-[#181D27] text-sm"> Designed 🎨 & Developed 👨🏻‍💻 by </p>
                <img
                    src={automation}
                    alt="Automation"
                    className="ml-2"
                />
            </div>

            <div className="hidden sm:flex items-center justify-end gap-4 w-[80%] sm:w-[40%]">
                <p className="text-[#181D27]">Need assistance?</p>
                <a
                    href="https://chat.google.com/room/AAAAXvY05KY"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <button className="bg-[#4D8C52] text-sm text-white px-4 py-[5px] cursor-pointer rounded hover:bg-green-700 transition">
                        Contact ERP Support
                    </button>
                </a>
            </div>
            <SupportPopup />

            {/* <div className='flex sm:hidden w-full h-full items-center justify-between !px-3'>
                <IconButton className={`flex flex-col items-center !rounded-[5px] !bg-[#4D8C52] !p-3`}><IoMdHome className='text-[#fff]' /></IconButton>
                <IconButton className={`flex flex-col items-center !rounded-[5px] !border-[1px] ! !border-[#4D8C52] !p-3`}><BsFillGridFill className='text-[#4D8C52]' /></IconButton>
                <IconButton className={`flex flex-col items-center !rounded-[5px] !border-[1px] ! !border-[#4D8C52] !p-3`}><BsPersonCheckFill className='text-[#4D8C52]' /></IconButton>
                <IconButton className={`flex flex-col items-center !rounded-[5px] !border-[1px] ! !border-[#4D8C52] !p-3`}><BsFillPersonLinesFill className='text-[#4D8C52]' /></IconButton>
            </div> */}
        </div> 
    );
};

export default Footer;
