import { useEffect, useState } from "react";
import { FaCaretRight } from "react-icons/fa";
import { InputBase, CircularProgress, Divider } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { ChevronDown, ChevronRight } from "lucide-react";
import {
  getAGKDepartments,
  getAGKFacilities,
  getAGKMis,
  getAGKProjects,
  getAGKRigs,
} from "../Utils/helpers";

const ProductsDrawer = () => {
  const [showDrawer, setShowDrawer] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [productData, setProductData] = useState<any>({
    projects: [],
    departments: [],
    rigs: [],
    facilities: [],
    mis: [],
  });

  const handleSearch = (e: any) => {
    setSearchValue(e.target.value);
  };

  const fetchData = async (label: string) => {
    setLoading(true);
    try {
      let res: any = [];
      switch (label) {
        case "Projects":
          res = await getAGKProjects();
          setProductData((prev: any) => ({ ...prev, projects: res }));
          break;
        case "Departments":
          res = await getAGKDepartments();
          setProductData((prev: any) => ({ ...prev, departments: res }));
          break;
        case "Rigs":
          res = await getAGKRigs();
          setProductData((prev: any) => ({ ...prev, rigs: res }));
          break;
        case "Facilities":
          res = await getAGKFacilities();
          setProductData((prev: any) => ({ ...prev, facilities: res }));
          break;
        case "MIS":
          res = await getAGKMis();
          setProductData((prev: any) => ({ ...prev, mis: res }));
          break;
        default:
          break;
      }
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const SidebarItem = ({ label, children, drawer, fetchData }: any) => {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<any>(children); // to store fetched children data

    useEffect(() => {
      if (!drawer) setOpen(false);
    }, [drawer]);

    const handleClick = async () => {
      if (!children && !data?.length) return; // no sub-items at all

      if (!open) {
        setLoading(true);
        const res = await fetchData(label); // API call
        setData(res); // update fetched data
        setLoading(false);
        setOpen(true);
      } else {
        setOpen(false);
      }
    };

    return (
      <div>
        <div
          onClick={handleClick}
          className={`flex justify-between font-[600] text-[#181D27] my-1 items-center px-2 py-2 rounded bg-[#F5F5F5] hover:bg-gray-200 ${children || data?.length ? "cursor-pointer" : "cursor-default"
            }`}
        >
          <span>{label}</span>
          {(children || data?.length) ? (open ? <ChevronDown size={16} /> : <ChevronRight size={16} />) : null}
        </div>

        {open && (
          <div className="ml-4 my-2 border-l pl-2">
            {loading ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : data?.length ? (
              data
            ) : (
              <div className="text-sm text-gray-400 italic">No Data Found</div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Toggle Button */}
      <div
        className={`fixed top-1/2 left-0 -translate-y-1/2 cursor-pointer py-8 px-1 z-[9999]  border-r border-gray-300 rounded-r-[5px] ${showDrawer ? "bg-[#4D8C52]" : "bg-[#FFF]"
          }`}
        onClick={() => {
          setShowDrawer(!showDrawer);
          setSearchValue("");
        }}
      >
        <FaCaretRight
          className={`text-[#4D8C52] transition-transform duration-300 ${showDrawer ? "rotate-180 text-[#FFF]" : "text-[#4D8C52]"
            }`}
          size={20}
        />
      </div>

      {/* Drawer */}
      <div
        className={`fixed top-0 left-0 h-full w-[90%] sm:w-[30%] bg-[#FFF] shadow-xl border-r transition-transform duration-300 z-[9998] ${showDrawer ? "translate-x-0" : "-translate-x-full"
          }`}
      >
        <div className="p-4 flex flex-col h-full">
          {/* Search */}
          <div className="relative mb-2 flex items-center border border-gray-300 rounded-lg px-2 sm:px-3 w-full">
            <SearchIcon className="text-gray-500" />
            <InputBase
              onChange={handleSearch}
              placeholder="Search Employee"
              className="ml-2 outline-none bg-transparent w-full text-gray-700 placeholder-gray-500"
            />
          </div>

          <Divider className="my-3" />

          {/* Data List */}
          {loading ? (
            <div className="flex justify-center items-center flex-1">
              <CircularProgress />
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2 mt-3 text-sm">
              <SidebarItem drawer={showDrawer} label="Projects">
                {productData?.projects?.map((project: any) => (
                  <div
                    key={project.code}
                    className="ml-4 text-gray-700 py-1 border-l pl-2"
                  >
                    {project.name1}
                  </div>
                ))}
              </SidebarItem>

              <SidebarItem drawer={showDrawer} label="Departments">
                {productData?.departments?.map((dep: any) => (
                  <div
                    key={dep.code}
                    className="ml-4 text-gray-700 py-1 border-l pl-2"
                  >
                    {dep.name1}
                  </div>
                ))}
              </SidebarItem>

              <SidebarItem drawer={showDrawer} label="Rigs">
                {productData?.rigs?.map((rig: any) => (
                  <div
                    key={rig.code}
                    className="ml-4 text-gray-700 py-1 border-l pl-2"
                  >
                    {rig.name1}
                  </div>
                ))}
              </SidebarItem>

              <SidebarItem drawer={showDrawer} label="Facilities">
                {productData?.facilities?.map((fac: any) => (
                  <div
                    key={fac.code}
                    className="ml-4 text-gray-700 py-1 border-l pl-2"
                  >
                    {fac.name1}
                  </div>
                ))}
              </SidebarItem>

              <SidebarItem drawer={showDrawer} label="MIS">
                {productData?.mis?.map((mis: any) => (
                  <div
                    key={mis.code}
                    className="ml-4 text-gray-700 py-1 border-l pl-2"
                  >
                    {mis.name1}
                  </div>
                ))}
              </SidebarItem>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default ProductsDrawer;
