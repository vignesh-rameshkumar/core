import { useEffect, useState, useRef } from "react";
import { FaCaretLeft } from "react-icons/fa";
import { InputBase, CircularProgress, Divider } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import profile from '../Assets/profile-vector.jpg'
import apiRequest from "../api/apiRequest";

const EmployeeSearchDrawer = () => {
  const [showDrawer, setShowDrawer] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (showDrawer)
      fetchEmployees('');
  }, [showDrawer]);

  const fetchEmployees = async (query: string) => {
    setLoading(true);
    let filter;
    filter = query && query !== "" ? `query=${query}` : ''
    try {
      const response = await apiRequest(`api/method/frappe.users.get_employees?start=0&limit=1000&${filter}`, "GET", "")
      if (response?.message) {
        setTimeout(() => {
          setLoading(false);
        }, 2000);
        const transformedArray = response?.message?.data
        setEmployees(transformedArray)
      }
    } catch (error) {
      console.error('Error getting data', error)
    } finally {
      setTimeout(() => {
        setLoading(false);
      }, 2000);
    }

  }
  const handleSearch = (e: any) => {
    const value = e.target.value;
    setSearchValue(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchEmployees(value);
    }, 500);
  };

  return (
    <>
      {/* Toggle Button */}
      <div
        className={`fixed top-1/2 right-0 -translate-y-1/2  text-white rounded-l cursor-pointer py-10 !z-9999 px-1 ${showDrawer ? "bg-[#4D8C52]" : "bg-[#FFF]"}`}
        onClick={() => { setShowDrawer(!showDrawer); setSearchValue('') }}
      >
        <FaCaretLeft
          className={` transition-transform duration-300 ${showDrawer ? "-rotate-180 text-[#FFF]" : "text-[#4D8C52]"
            }`}
        />
      </div>

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-[90%] sm:w-[30%] bg-[#FFF] shadow-lg border-l transition-transform duration-300 z-999 ${showDrawer ? "translate-x-0" : "translate-x-full"
          }`}
      >
        <div className="p-4 border-b">
          <div className="relative flex items-center border border-gray-300 rounded-lg px-2 sm:px-3 w-full">
            <SearchIcon className="text-gray-500" />

            <InputBase
              onChange={handleSearch}
              placeholder="Search Employee"
              className="ml-2 outline-none bg-transparent w-full text-gray-700 placeholder-gray-500"
            />
          </div>
        </div>
        <Divider />

        {loading ? (
          <div className="flex justify-center items-center h-[80%]">
            <CircularProgress className="!text-[#4D8C52]"/>
          </div>
        ) : (
          <>
            {employees.length > 0 ? (
              <div className="p-4 space-y-3 overflow-y-auto h-[calc(100vh-80px)]">
                {employees.map((emp: any, idx: number) => (
                  <div
                    key={idx}
                    className="border rounded-xl p-3 shadow space-y-1 bg-[#F5F5F5]"
                  >
                    <div className="flex items-center gap-2">
                      <img
                        src={emp.user_image || profile}
                        alt="emp"
                        className="h-12 w-12 rounded-full object-cover"
                      />
                      <div className="flex-1">
                        <div className="font-semibold text-[#222]">{emp.full_name}</div>
                        <div className="text-xs text-gray-700">
                          {emp.department}
                        </div>

                      </div>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${emp.status === "Online"
                          ? "bg-green-100 text-green-600"
                          : "bg-red-100 text-red-600"
                          }`}
                      >
                        {emp.status}
                      </span>
                    </div>
                    <div className="flex mt-4 w-full">
                      <div className="text-sm text-[#181D27] w-[15%]">Email</div>
                      <div className="text-sm font-bold text-[#181D27] mx-3">{emp.email || "-"}</div>
                    </div>
                    <div className="flex w-full">
                      <div className="text-sm text-[#181D27] w-[15%]">Mobile</div>
                      <div className="text-sm font-bold text-[#181D27] mx-3">{emp.phone || "-"}</div>
                    </div>
                    <div className="flex w-full">
                      <div className="text-sm text-[#181D27] w-[15%]">Location</div>
                      <div className="text-sm font-bold text-[#181D27] mx-3">
                        {emp.location || "NA"}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex justify-center items-center h-[80%] text-gray-400">
                No Employee Found
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
};

export default EmployeeSearchDrawer;
