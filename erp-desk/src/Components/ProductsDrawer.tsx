import { useRef, useState } from "react";
import { FaCaretRight } from "react-icons/fa";
import { InputBase, Divider, CircularProgress } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { getAGKDepartments, getAGKFacilities, getAGKMis, getAGKProjects, getAGKRigs, mappingLabels, SidebarItem } from "../Utils/helpers";
import { IoIosRocket } from "react-icons/io";
import DotLoader from "./loder";
import apiRequest from "../api/apiRequest";


const ProductsDrawer = () => {
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const [showDrawer, setShowDrawer] = useState(false);
  const [search, setSearch] = useState("");
  const [searchData, setSearchData] = useState({});
  const [loading, setLoading] = useState<{ [key: string]: boolean }>({});
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [productData, setProductData] = useState({
    projects: [],
    departments: [],
    rigs: [],
    facilities: [],
    mis: [],
  });

  const fetchSearchData = async (query: string) => {
    setSearchLoading(true);
    let filter;
    filter = query && query !== "" ? `query=${query}` : ''
    try {
      const response = await apiRequest(`/api/method/core.api.search.search?&${filter}`, "GET", "")
      if (response?.message) {
        setTimeout(() => {
          setSearchLoading(false);
        }, 2000);
        const transformedArray = response?.message
        setSearchData(transformedArray)
      }
    } catch (error) {
      console.error('Error getting data', error)
    } finally {
      setTimeout(() => {
        setSearchLoading(false);
      }, 1000);
    }

  }

  const handleSearch = (e: any) => {
    const value = e.target.value;
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchSearchData(value);
    }, 500);
  };

  const fetchData = async (type: string) => {
    setLoading((prev) => ({ ...prev, [type]: true }));

    let tempData = [];

    switch (type) {
      case "Projects":
        tempData = await getAGKProjects();
        break;
      case "Departments":
        tempData = await getAGKDepartments();
        break;
      case "Rigs":
        tempData = await getAGKRigs();
        break;
      case "Facilities":
        tempData = await getAGKFacilities();
        break;
      case "MIS":
        tempData = await getAGKMis();
        break;
    }

    setProductData((prev) => ({
      ...prev,
      [type.toLowerCase()]: tempData || [],
    }));

    setTimeout(() => {
      setLoading((prev) => ({ ...prev, [type]: false }));
    }, 2000);
  };

  return (
    <>
      {/* Toggle Button */}
      <div
        className={`fixed top-1/2 left-0 -translate-y-1/2 cursor-pointer py-10 px-1 z-[9999]  border-r border-gray-300 rounded-r-[5px] ${showDrawer ? "bg-[#4D8C52]" : "bg-[#FFF]"}`}
        onClick={() => { setShowDrawer(!showDrawer); setSearch('') }}
      >
        <FaCaretRight
          className={`text-[#4D8C52] transition-transform duration-300 ${showDrawer ? "rotate-180 text-[#FFF]" : "text-[#4D8C52]"}`}
        />
      </div>

      {/* Drawer */}
      <div
        className={` fixed top-0 left-0 h-full w-[90%] sm:w-[30%] bg-[#FFF] shadow-xl border-r transition-transform duration-300 z-[9998] ${showDrawer ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="p-4 flex flex-col h-full">
          {/* Search */}
          <div className="relative mb-2 flex items-center border border-gray-300 rounded-lg px-2 sm:px-3 w-full">
            <SearchIcon className="text-gray-500" />
            <InputBase
              onChange={handleSearch}
              placeholder="Search"
              className="ml-2 outline-none bg-transparent w-full text-gray-700 placeholder-gray-500"
            />
          </div>

          <Divider className="my-3" />

          {/* Search Product List / Menu */}
          {(!search && search.trim() === "") ?
            <div className="flex-1 overflow-y-auto h-[calc(100vh-200px)] space-y-2 mt-3 text-sm">

              {/* Nested Sidebar */}
              <SidebarItem drawer={showDrawer} label="Projects" onHandle={() => { fetchData('Projects') }}>
                {loading["Projects"] ?
                  <div className="flex justify-center items-center flex-1">
                    <DotLoader />
                  </div>
                  : <>
                    {productData?.projects?.length > 0 ? productData?.projects?.map((project: any, index: number) => (
                      <SidebarItem
                        key={index}
                        drawer={showDrawer}
                        label={project?.name1}
                        code={project?.code}
                      />

                    )) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No Projects Found --- </div>}
                  </>}
              </SidebarItem>
              <SidebarItem drawer={showDrawer} label="Departments" onHandle={() => { fetchData('Departments') }}>
                {loading["Departments"] ?
                  <div className="flex justify-center items-center flex-1">
                    <DotLoader />
                  </div>
                  : <>  {productData?.departments?.length > 0 ? productData?.departments?.map((depart: any, index: number) => (
                    <SidebarItem
                      key={index}
                      drawer={showDrawer}
                      label={depart.department_name}
                      code={depart?.department_code}
                    />
                  )) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No Departments Found --- </div>}
                  </>}
              </SidebarItem>
              <SidebarItem drawer={showDrawer} label="Facilities" onHandle={() => { fetchData('Facilities') }}>
                {loading["Facilities"] ?
                  <div className="flex justify-center items-center flex-1">
                    <DotLoader />
                  </div>
                  : <>  {productData?.facilities?.length > 0 ? productData?.facilities?.map((fac: any, index: number) => (
                    <SidebarItem
                      key={index}
                      drawer={showDrawer}
                      label={fac.facility_name}
                      code={fac?.facility_code}
                    />
                  )) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No Facilities Found --- </div>}
                  </>}
              </SidebarItem>
              <SidebarItem drawer={showDrawer} label="Rigs" onHandle={() => { fetchData('Rigs') }}>
                {loading["Rigs"] ?
                  <div className="flex justify-center items-center flex-1">
                    <DotLoader />
                  </div>
                  : <>  {productData?.rigs?.length > 0 ? productData?.rigs?.map((rig: any, index: number) => (
                    <SidebarItem
                      key={index}
                      drawer={showDrawer}
                      label={rig.rig_name}
                      code={rig?.rig_code}
                    />
                  )) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No Rigs Found --- </div>}
                  </>}
              </SidebarItem>
              <SidebarItem drawer={showDrawer} label="MIS" onHandle={() => { fetchData('MIS') }}>
                {loading["MIS"] ?
                  <div className="flex justify-center items-center flex-1">
                    <DotLoader />
                  </div>
                  : <>  {productData?.mis?.length > 0 ? productData?.mis?.map((misData: any, index: number) => (
                    <SidebarItem
                      key={index}
                      drawer={showDrawer}
                      label={misData.name}
                      isProduct={misData?.is_product ? true : false}
                      code={misData?.mis_indicator}
                    >
                      {misData?.sub_categories?.length > 0 ? misData?.sub_categories?.map((subData: any, idx: number) =>
                        <SidebarItem
                          key={idx}
                          drawer={showDrawer}
                          label={subData.category}
                          code={subData?.mis_indicator}
                        />) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No Sub-Category Found --- </div>}
                    </SidebarItem>
                  )) : <div className="my-5 flex justify-center items-center h-[80%] text-gray-400"> --- No MIS Found --- </div>}
                  </>}
              </SidebarItem>

            </div>
            : <div className="mt-3 border border-gray-200 rounded p-1 ">
              <div className="flex justify-between items-center px-2 py-2 rounded bg-[#F5F5F5] hover:bg-gray-200 text-[#181D27]">
                Search Results
              </div>
              {searchLoading ? (
                <div className="flex justify-center items-center mt-2 h-[calc(100vh-200px)]">
                  <CircularProgress className="!text-[#4D8C52]" />
                </div>
              ) : (
                <div className="mt-2 space-y-2 overflow-y-auto h-[calc(100vh-200px)]">

                  {Object.values(searchData).every((value: any) => value.length === 0) ? (
                    <div className="my-5 flex justify-center items-center h-[80%] text-gray-400">
                      --- No Search Found ---
                    </div>
                  ) : (
                    Object.entries(searchData).map(([key, value]: any) =>
                      value.length > 0 && (
                        <div key={key}>
                          <div className="text-sm font-semibold text-gray-800 px-2 py-1">
                            {mappingLabels[key]}
                          </div>

                          <div className="pl-3 pt-1 space-y-1">
                            {value.map((item: any, index: number) => (
                              <div
                                key={index}
                                className="text-sm text-gray-600 gap-2 w-full rounded px-2 py-1 flex justify-between items-center"
                              >
                                <span>{item?.name || "-"}</span>
                                <span>{item?.code || "-"}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )
                  )}
                </div>
              )}

            </div>
          }
        </div>
        <div className="absolute bottom-2 right-2 flex items-center rounded-full ">
          <IoIosRocket className=" text-[#4D8C52] mr-2" />
          <div className="text-gray-700">- Product</div>
        </div>
      </div>
    </>
  );
};

export default ProductsDrawer;
