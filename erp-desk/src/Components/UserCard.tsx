import userCard from '../Assets/usercard.png'
import LogoutIcon from '@mui/icons-material/Logout';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import LoginIcon from '@mui/icons-material/Login';
import WorkingHoursBarGraph from './workingHoursBarGraph';
import React, { useEffect, useState } from 'react';
import { getEmployeeActivity } from '../Utils/helpers';
const UserCard: React.FC<any> = ({ }) => {
    const [empData, setEmpData] = useState({})
    const data = {
        Mon: 8,
        Tue: 5,
        Wed: 0,
        Thur: 6,
        Fri: 2,
        Sat: 0,
        Sun: 0,
    };
    useEffect(() => {
        const employeeData = async () => {
            const temp = await getEmployeeActivity()
            console.log(temp);
        }
        employeeData()
    }, [])


    return (
        <div className="w-full h-auto sm:h-[280px] !rounded-lg">
            <div style={{ backgroundImage: `url(${userCard})` }} className="w-full h-full  !rounded-lg text-white bg-cover bg-center bg-no-repeat p-4"  >
                <div className='flex flex-col sm:flex-row'>
                    <h1 className='font-[600] text-2xl'>Hello,</h1>
                    <h1 className='font-[600] text-2xl'>  👋🏻</h1>

                </div>
                <div className='flex flex-wrap my-2 w-full gap-3 !mb-3'>
                    <div className='w-full sm:w-[52%] flex gap-3'>
                        {/* Login */}
                        <div className='w-1/2 bg-[#FFFFFF99] p-2 rounded-[10px]'>
                            <div className='flex items-center justify-between text-[#222]'>
                                Login
                                <LoginIcon className='text-[#222] !text-lg ' />
                            </div>
                            <h2 className='font-bold text-[#181D27]'>09:23 AM</h2>
                        </div>
                        {/* Logout */}
                        <div className='w-1/2 bg-[#FFFFFF99] p-2 rounded-[10px]'>
                            <div className='flex items-center justify-between text-[#222]'>
                                Logout
                                <LogoutIcon className='text-[#222] !text-lg ' />
                            </div>
                            <h2 className='font-bold text-[#181D27]'>09:23 AM</h2>
                        </div>
                    </div>
                    {/* Total Working Hours */}
                    <div className='w-full md:flex-1 bg-[#FFFFFF99] p-2 rounded-[10px]'>
                        <div className='flex items-center justify-between text-[#222]'>
                            Total Working hrs
                            <AccessTimeIcon className='rounded-full  text-[#222] !text-lg ' />
                        </div>
                        <h2 className='font-bold text-[#181D27]'>09H 23M</h2>
                    </div>

                </div>


                <WorkingHoursBarGraph data={data} />

            </div>

        </div>

    )
}

export default UserCard