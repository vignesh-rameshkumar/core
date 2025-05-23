import apiRequest from "../api/apiRequest";
import { Tooltip, tooltipClasses, TooltipProps } from '@mui/material';
import { styled } from '@mui/material/styles';
import { ChevronDown, ChevronRight } from "lucide-react";
import { SetStateAction, useEffect, useState } from "react";
import { IoIosRocket } from "react-icons/io";
import { toast } from "react-toastify";

interface ContainerType {
    idx: number;
    name: string;
    icon: string;
    apps: AppType[];
}
interface AppType {
    idx: number;
    label: string;
    icon: string;
    route: string;
    departments: string[];
    roles: string[];
}


export const mappingLabels: any = {
    projects: "Projects",
    departments: "Departments",
    facilities: "Facilities",
    rigs: "Rigs",
    mis: "MIS",
};

export const handleNavigateSearch = (name: string) => {
    const path = name.toLowerCase().replace(/\s+/g, "-");
    window.location.href = `/app/${path}`;
};
export const filterContainers = (
    containers: ContainerType[],
    userRoles: string[],
    userDepartment: string
): ContainerType[] => {
    return containers
        .map((container) => ({
            ...container,
            apps: container.apps.filter(
                (app) =>
                    app.roles.some((role) => userRoles.includes(role)) ||
                    app.departments.includes(userDepartment)
            ),
        }))
        .filter((container) => container.apps.length > 0);
};

export const getUserDetails = async () => {
    try {
        const response = await apiRequest(`/api/method/core.get_roles`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return {}
        }

    } catch (error) {
        console.error('Error getting data', error)
    }
}
export const handleCopy = (text: string, field: "email" | "phone", index: number, setCopiedField: SetStateAction<any>) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField({ index, field });
    setTimeout(() => setCopiedField(null), 1500);
};


export const calculateWorkingHours = (logInTimeStr: string): string => {
    if (!logInTimeStr) return "-"
    const [logInHours, logInMinutes] = logInTimeStr?.split(':')?.map(Number);

    const now = new Date();
    const logInTime = new Date();
    logInTime?.setHours(logInHours, logInMinutes, 0, 0);

    const diffMs = now?.getTime() - logInTime?.getTime();

    if (diffMs < 0) return "Invalid time"; // in case login is in future

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    return `${diffHours}h ${diffMinutes}m`;
}
export function convertTimeStringToReadable(timeStr: string): string {
    const [hoursStr, minutesStr] = timeStr?.split(':');
    const hours = parseInt(hoursStr, 10);
    const minutes = parseInt(minutesStr, 10);

    return `${hours}h ${minutes}m`;
}


export const clearCacheData = async () => {
    try {
        const response = await apiRequest(`/api/method/frappe.sessions.clear`, "GET", "")
        if (response) {
            toast.info("Cache Cleared !", {
                position: "bottom-right",
            });
            setTimeout(() => {
                window.location.reload()
            }, 1000);
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}
export const getEmployeeActivity = async () => {
    try {
        const response = await apiRequest(`/api/method/payroll_management.api.quick_access?lop_month=All`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return {}
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}


export const getEmployeeActivityGraph = async () => {
    try {
        const response = await apiRequest(`/api/method/payroll_management.api.week_chart?week_offset=0`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}

export const getAGKProjects = async () => {
    try {
        const response = await apiRequest(`/api/method/core.api.projects.list?limit=100000&start=0`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message?.details
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}

export const getAGKRigs = async () => {
    try {
        const response = await apiRequest(`/api/method/core.api.rigs.list`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}

export const getAGKDepartments = async () => {
    try {
        const response = await apiRequest(`/api/method/core.api.departments.list`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}

export const getAGKFacilities = async () => {
    try {
        const response = await apiRequest(`/api/method/core.api.facility.list`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}
export const getAGKMis = async () => {
    try {
        const response = await apiRequest(`/api/method/core.api.mis.list`, "GET", "")
        if (response?.message) {
            const transformedArray = response?.message
            return transformedArray
        } else {
            return []
        }
    } catch (error) {
        console.error('Error getting data', error)
    }
}

export const getModules = async () => {
    try {
        const response = await apiRequest(`/api/method/core.get_desk_data`, 'GET', '');
        if (response?.message) {
            const transformedArray = response?.message?.containers;
            return transformedArray
        } else {
            return []
        }
    }
    catch {
        console.error('Something went wrong!!!')
        return []
    }
}

export const CustomTooltip = styled(({ className, ...props }: TooltipProps) => (
    <Tooltip {...props} classes={{ popper: className }} />
))(() => ({
    [`& .${tooltipClasses.tooltip} `]: {
        backgroundColor: '#fff',
        color: '#181D27',
        boxShadow: '0px 2px 8px rgba(0,0,0,0.1)',
        fontSize: '12px',
        borderRadius: '6px',
        padding: '6px 10px',
    },
}));

export const mapGraphData = (apiData: any): any => {
    const dayMap: { [key: string]: string } = {
        M: 'Mon',
        T: 'Tue',
        W: 'Wed',
        TH: 'Thu',
        F: 'Fri',
        S: 'Sat',
        SU: 'Sun',
    };

    const result: any = {
        Mon: 0,
        Tue: 0,
        Wed: 0,
        Thu: 0,
        Fri: 0,
        Sat: 0,
        Sun: 0,
    };

    if (!Array.isArray(apiData)) return result; // Safety check

    apiData.forEach((item) => {
        const [shortDay, , hours] = item;
        const day = dayMap[shortDay];

        if (day) {
            result[day] = Array.isArray(item[1]) ? 0 : hours || 0;
        }
    });

    return result;
};

export const SidebarItem = ({ label, code, children, drawer, onHandle, isProduct }: any) => {
    const [open, setOpen] = useState(false);

    useEffect(() => {
        if (!drawer) setOpen(false);
    }, [drawer]);

    const handleClick = () => {
        if (onHandle) {
            onHandle(label)
        }
        if (children) {
            setOpen(!open);
        }
    };

    return (
        <div>
            <div
                onClick={handleClick}
                className={`flex justify-between  text-[#181D27] my-1  items-center px-2 py-2 rounded bg-[#F5F5F5] hover:bg-gray-200 ${children ? "cursor-pointer" : "cursor-default"
                    }`}
            >
                <div className="flex  text-[#181D27]">

                    <span className="font-[600] mr-2">{label}</span>
                    {code &&
                        <span>{" ("}{code}{")"}</span>}

                </div>

                {children ? <div className="flex">
                    {isProduct && <IoIosRocket className=" text-[#4D8C52] mr-2" />}
                    {open ? (
                        <ChevronDown size={16} />
                    ) : (
                        <ChevronRight size={16} />
                    )}
                </div> : null}
            </div>

            {open && children && (
                <div className="ml-4 my-2 border-l pl-2">{children}</div>
            )}
        </div>
    );
};
