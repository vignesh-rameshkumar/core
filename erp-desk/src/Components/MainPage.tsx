import bgImage from '../Assets/background.png';
import ModuleCard from './ModuleCard';
import UserCard from './UserCard';

import { IoPersonCircleOutline } from "react-icons/io5";
import { TbTimeline } from "react-icons/tb";
import { PiSuitcaseSimpleFill } from "react-icons/pi";
import { AiFillTool } from "react-icons/ai";
import { PiStackFill } from "react-icons/pi";
import { FaCreditCard } from "react-icons/fa6";
import EmployeeSearchDrawer from './EmployeeSearchDrawer';
import { useEffect, useState } from 'react';
import { getEmployeeDetails } from '../Utils/helpers';



const MainPage = () => {
    const [employeeData, setEmployeeData] = useState({})
    const sampleData = [
        {
            idx: 1,
            name: "Employee Wellness",
            icon: <IoPersonCircleOutline className="text-[#535862] !mx-2 !text-3xl" />,
            apps: [
                {
                    idx: 1,
                    label: "Payroll Management",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/payroll_desk",
                    departments: ["HR", "Finance"],
                    roles: ["Payroll Manager", "HR Assistant"]
                },
                {
                    idx: 2,
                    label: "Leave r",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 text-3xl" />,
                    route: "/leave_tracker",
                    departments: ["HR"],
                    roles: ["HR Assistant", "Employee"]
                },
                {
                    idx: 3,
                    label: "Leave Tracker",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/leave_tracker",
                    departments: ["HR"],
                    roles: ["HR Assistant", "Employee"]
                },
                {
                    idx: 4,
                    label: "Leave Tracker",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/leave_tracker",
                    departments: ["HR"],
                    roles: ["HR Assistant", "Employee"]
                },
                {
                    idx: 5,
                    label: "Leave Tracker",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/leave_tracker",
                    departments: ["HR"],
                    roles: ["HR Assistant", "Employee"]
                }
            ]
        },
        {
            idx: 2,
            name: "IT Services",
            icon: <IoPersonCircleOutline className="text-[#535862] !mx-2 !text-3xl" />,
            apps: [
                {
                    idx: 1,
                    label: "Asset Management",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/asset_desk",
                    departments: ["IT"],
                    roles: ["IT Admin", "Technician"]
                },
                {
                    idx: 2,
                    label: "Support Desk",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/support_desk",
                    departments: ["IT", "All"],
                    roles: ["All"]
                }
            ]
        },
        {
            idx: 3,
            name: "IT Services",
            icon: <IoPersonCircleOutline className="text-[#535862] !mx-2 !text-3xl" />,
            apps: [
                {
                    idx: 1,
                    label: "Asset Management",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/asset_desk",
                    departments: ["IT"],
                    roles: ["IT Admin", "Technician"]
                },
                {
                    idx: 2,
                    label: "Support Desk",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/support_desk",
                    departments: ["IT", "All"],
                    roles: ["All"]
                }
            ]
        },
        {
            idx: 4,
            name: "IT Services",
            icon: <IoPersonCircleOutline className="text-[#535862] !mx-2 !text-3xl" />,
            apps: [
                {
                    idx: 1,
                    label: "Asset Management",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/asset_desk",
                    departments: ["IT"],
                    roles: ["IT Admin", "Technician"]
                },
                {
                    idx: 2,
                    label: "Support Desk",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/support_desk",
                    departments: ["IT", "All"],
                    roles: ["All"]
                }
            ]
        },
        {
            idx: 5,
            name: "IT Services",
            icon: <IoPersonCircleOutline className="text-[#535862] !mx-2 !text-3xl" />,
            apps: [
                {
                    idx: 1,
                    label: "Asset Management",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/asset_desk",
                    departments: ["IT"],
                    roles: ["IT Admin", "Technician"]
                },
                {
                    idx: 2,
                    label: "Support Desk",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/support_desk",
                    departments: ["IT", "All"],
                    roles: ["All"]
                },
                {
                    idx: 3,
                    label: "Support Desk",
                    icon: <FaCreditCard className="text-[#4D8C52] !mx-2 !text-3xl" />,
                    route: "/support_desk",
                    departments: ["IT", "All"],
                    roles: ["All"]
                }
            ]
        }
    ]
    useEffect(() => {
        const data = getEmployeeDetails();
        setEmployeeData(data)
    }, [])

    return (
        <div className="bg-cover bg-center h-screen w-full !overflow-hidden"
            style={{ backgroundImage: `url(${bgImage})` }}
        >
            <EmployeeSearchDrawer />
            {JSON.stringify(employeeData)}
            <div className='grid grid-cols-1 md:grid-cols-3 gap-6 h-full overflow-y-auto py-25 px-5 sm:px-15'>
                <UserCard />
                {sampleData?.map((data: any) => <ModuleCard data={data} />)}
            </div>
        </div>

    )
}

export default MainPage