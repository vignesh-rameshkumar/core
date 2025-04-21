import { useEffect, useState, useRef } from "react";
import { FaCaretLeft } from "react-icons/fa";
import { InputBase, CircularProgress, Divider } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import InfiniteScroll from "react-infinite-scroll-component";
import profile from "../Assets/profile-vector.jpg";
import apiRequest from "../api/apiRequest";
import { handleCopy } from "../Utils/helpers";
import { MdContentCopy } from "react-icons/md";


const EmployeeSearchDrawer = () => {
  const [showDrawer, setShowDrawer] = useState(false);
  const [employees, setEmployees] = useState<any>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [start, setStart] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedField, setCopiedField] = useState<{ index: number; field: "email" | "phone" } | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showDrawer) {
      resetAndFetchEmployees("");
    }
  }, [showDrawer]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        drawerRef.current &&
        !drawerRef.current.contains(event.target as Node) &&
        (event.target as HTMLElement).closest(".drawer-toggle-btn") === null
      ) {
        setShowDrawer(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const resetAndFetchEmployees = async (query: string) => {
    setEmployees([]);
    setStart(0);
    setSearchQuery(query);
    setHasMore(true);
    fetchEmployees(0, query);
  };

  const fetchEmployees = async (startIndex: number, query: string = "") => {
    setLoading(true);
    try {
      const filter = query ? `&query=${query}` : "";
      const response = await apiRequest(
        `api/method/frappe.users.get_employees?start=${startIndex}&limit=20${filter}`,
        "GET",
        ""
      );
      const result = response?.message?.data || [];
      const hasMoreFlag = response?.message?.has_more;

      setEmployees((prev: any) => [...prev, ...result]);
      setHasMore(hasMoreFlag);
      setStart(response?.message?.next_start || startIndex + 20);
    } catch (error) {
      console.error("Error fetching employees:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: any) => {
    const value = e.target.value;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      resetAndFetchEmployees(value);
    }, 500);
  };

  return (
    <>
      {/* Toggle Button */}
      <div
        className={`fixed top-1/2 right-0 -translate-y-1/2 text-white rounded-l cursor-pointer py-10 !z-9999 px-1 ${showDrawer ? "bg-[#4D8C52]" : "bg-[#FFF]"} drawer-toggle-btn`}
        onClick={() => setShowDrawer(!showDrawer)}
      >
        <FaCaretLeft
          className={`transition-transform duration-300 ${showDrawer ? "-rotate-180 text-[#FFF]" : "text-[#4D8C52]"}`}
        />
      </div>

      {/* Drawer */}
      <div
        ref={drawerRef}
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

        {loading && employees.length === 0 ? (
          <div className="flex justify-center items-center h-[80%]">
            <CircularProgress className="!text-[#4D8C52]" />
          </div>
        ) : (
          <InfiniteScroll
            dataLength={employees.length}
            next={() => fetchEmployees(start, searchQuery)}
            hasMore={hasMore}
            loader={
              <div className="flex justify-center py-4">
                <CircularProgress size={24} className="!text-[#4D8C52]" />
              </div>
            }
            height={"calc(100vh - 80px)"}
            endMessage={
              <div className="text-center py-4 text-sm text-gray-400">
                No more employees
              </div>
            }
          >
            <div className="p-4 space-y-3">
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
                      <div className="text-xs text-gray-700">{emp.department}</div>
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

                  {/* Email Row */}
                  <div className="flex mt-4 w-full items-center">
                    <div className="text-sm text-[#181D27] w-[15%]">Email</div>
                    <div className="text-sm font-bold text-[#181D27] mx-3 flex items-center gap-2 relative">
                      {emp.email || "-"}
                      {emp.email && (
                        <>
                          <MdContentCopy
                            size={16}
                            className="cursor-pointer text-gray-500 hover:text-black"
                            onClick={() => handleCopy(emp.email, "email", idx, setCopiedField)}
                          />
                          {copiedField?.index === idx &&
                            copiedField.field === "email" && (
                              <span className="absolute top-[-20px] right-0 text-xs text-green-600 bg-white px-2 rounded shadow">
                                Email Copied
                              </span>
                            )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Phone Row */}
                  <div className="flex w-full items-center">
                    <div className="text-sm text-[#181D27] w-[15%]">Mobile</div>
                    <div className="text-sm font-bold text-[#181D27] mx-3 flex items-center gap-2 relative">
                      {emp.phone || "-"}
                      {emp.phone && (
                        <>
                          <MdContentCopy
                            size={16}
                            className="cursor-pointer text-gray-500 hover:text-black"
                            onClick={() => handleCopy(emp.phone, "phone", idx, setCopiedField)}
                          />
                          {copiedField?.index === idx &&
                            copiedField.field === "phone" && (
                              <span className="absolute top-[-20px] left-0 text-xs text-green-600 bg-white px-2 rounded shadow">
                                Number Copied
                              </span>
                            )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Location */}
                  <div className="flex w-full">
                    <div className="text-sm text-[#181D27] w-[15%]">Location</div>
                    <div className="text-sm font-bold text-[#181D27] mx-3">
                      {emp.location || "NA"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </InfiniteScroll>
        )}
      </div>
    </>
  );
};

export default EmployeeSearchDrawer;
