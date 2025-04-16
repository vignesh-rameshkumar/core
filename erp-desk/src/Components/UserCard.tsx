import userCard from '../Assets/usercard.png'
import LogoutIcon from '@mui/icons-material/Logout';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import LoginIcon from '@mui/icons-material/Login';
import WorkingHoursBarGraph from './workingHoursBarGraph';
import React, { useEffect, useState } from 'react';
import { getEmployeeActivity, getEmployeeActivityGraph } from '../Utils/helpers';
import dayjs from 'dayjs';
import { useSelector } from 'react-redux';
import { RootState } from '../Store';
const UserCard: React.FC<any> = ({ }) => {
    const [empData, setEmpData] = useState<any>({})
    const [graphData, setGraphData] = useState({})
    const { userData } = useSelector((state: RootState) => state.user);

    useEffect(() => {
        const employeeData = async () => {
            const tempData: any = await getEmployeeActivity();
            const tempGraph: any = await getEmployeeActivityGraph();
            setGraphData(tempGraph)
            setEmpData(tempData);
        }
        employeeData();
    }, [])

    return (
        <div className="w-full h-auto sm:h-[320px] !rounded-lg ">
            <div style={{ backgroundImage: `url(${userCard})` }} className="w-full h-full  !rounded-lg text-white bg-cover bg-center bg-no-repeat p-4"  >
                <div className='flex w-full justify-between items-start'>
                    <h1 className='font-[600] text-xl pr-1'>👋🏻 Hello, {userData?.employee_name || "User"}{" "}</h1>
                    <h1 className='w-[30%] text-right font-[600] text-xl text-[#B6F2BA]'>{dayjs(new Date()).format('MMMM, DD')}</h1>
                </div>
                <div className='flex flex-wrap my-2 w-full gap-3 !mb-3'>
                    <div className='w-full sm:w-[52%] flex gap-3'>
                        {/* Login */}
                        <div className='w-1/2 bg-[#FFFFFF99] p-2 rounded-[10px] border-[1px] border-[#FFFFFF33]'>
                            <div className='flex items-center justify-between text-[#535862]'>
                                Login
                                <LoginIcon className='text-[#535862] !text-lg ' />
                            </div>
                            <h2 className='font-bold text-[#181D27]'>{empData?.todays_att?.log_in || "-"}</h2>
                        </div>
                        {/* Logout */}
                        <div className='w-1/2 bg-[#FFFFFF99] p-2 rounded-[10px]'>
                            <div className='flex items-center justify-between text-[#535862]'>
                                Logout
                                <LogoutIcon className='text-[#535862] !text-lg ' />
                            </div>
                            <h2 className='font-bold text-[#181D27]'>{empData?.todays_att?.log_out || "-"}</h2>
                        </div>
                    </div>
                    {/* Total Working Hours */}
                    <div className='w-full md:flex-1 bg-[#FFFFFF99] p-2 rounded-[10px]'>
                        <div className='flex items-center justify-between text-[#535862]'>
                            Total Working hrs
                            <AccessTimeIcon className='rounded-full  text-[#535862] !text-lg ' />
                        </div>
                        <h2 className='font-bold text-[#181D27]'>{empData?.monthly_data?.total_working_hours || "-"}</h2>
                    </div>
                </div>
                <WorkingHoursBarGraph data={graphData} />
            </div>
        </div>
    )
}

export default UserCard