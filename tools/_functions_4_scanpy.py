def df_loadings_ordered_byPC(adata,ascending=False,
save_table=False,output_dir="./adata_output/",output_prefix="adata_",#**parameters
                            ):
    """
    ######################## idea from https://github.com/scverse/scanpy/issues/836
    """
    import os
    import numpy as np
    import pandas as pd
    import scanpy as sc
    os.makedirs(output_dir+output_prefix, exist_ok=True)
    os.makedirs(output_dir+output_prefix+'/tables/', exist_ok=True)
    
    dataset_tables_output_directory=output_dir+output_prefix+'/tables/'
    
    df_loadings = pd.DataFrame(adata.varm['PCs'], index=adata.var_names)
    df_loadings_ordered_byPC=pd.DataFrame()
    for i in df_loadings.columns:
        df_loadings_ordered_byPC['PC_'+str(i+1)+'_n']=df_loadings[df_loadings.columns[i]].sort_values(ascending=ascending).index.tolist()
        df_loadings_ordered_byPC['PC_'+str(i+1)+'_val']=df_loadings[df_loadings.columns[i]].sort_values(ascending=ascending).tolist()
    if save_table==True:
        if ascending==False:
            df_loadings_ordered_byPC.to_csv(dataset_tables_output_directory+output_prefix+"PC_embedings_POS.csv")
        if ascending==True:
            df_loadings_ordered_byPC.to_csv(dataset_tables_output_directory+output_prefix+"PC_embedings_NEG.csv")
    return df_loadings_ordered_byPC



def cef_to_adata(data_dir,data_prefix,n_obs=0,n_skiprows=2,cef_delimiter_tab=True,save_to_h5ad=True):
    """
    this 
    cef_to_adata_float()
    is for count files with float values
    """
    import anndata
    import pandas as pd
    import scanpy as sc
    import numpy as np
    
    output_prefix=data_prefix
    if cef_delimiter_tab==True:
        df = pd.read_csv(data_dir+data_prefix, skiprows=n_skiprows, delimiter= '\t',low_memory=False)
    else:
        df = pd.read_csv(data_dir+data_prefix, skiprows=n_skiprows,low_memory=False)

    ######################################### Make gene list    
    genes = df.iloc[1+n_obs:,0].str.upper()
    df_genes = pd.DataFrame(data=genes)
    df_genes =df_genes.set_index(df_genes.columns[0])
    #df_genes = pd.DataFrame()
    #df_genes['Gene']=genes
    #df_genes = df_genes.set_index('Gene')
    ######################################### Make gene list   END

    ######################################### Make cell annoation data frame    
    obs = df.iloc[:0+n_obs,1:].set_index(df.columns[1]).T

    ######################################### Make cell annoation data frame    END  

    ######################################### Make counts array  

    X = df.iloc[1+n_obs:,2:].values.T
    X.shape

    ######################################### Make counts array  END

    ######################################### Make adata object  
    adata = anndata.AnnData(X = X, var = df_genes, obs = obs, dtype=np.float32 )
    ######################################### Make counts array  END
    if save_to_h5ad==True:
        ######################################### save adata object  to .h5ad file in same directory
        adata.write_h5ad(data_dir+output_prefix+'.h5ad',compression='gzip')
        ######################################### save adata object  to .h5ad file in same directory END
    
    return adata
####################################### add better doc string here  and make example in note book
def ann_cells_4_marker_gene(adata,gene_names,min_n_counts=0,obs_key='cell_pos'):
    #make true false array with demensions cells x genes
    #gene_names=["TH","EN1",'PITX3','PITX2',
    import numpy as np
    cell_gene_array_all=adata.raw.to_adata()[:,gene_names[0]].X.toarray()>min_n_counts
    for gene in gene_names[1:]:
        cell_gene_array_all=np.hstack((cell_gene_array_all,(adata.raw.to_adata()[:,gene].X.toarray()>min_n_counts)))
    #make list of names for each combiantion of results
    cell_pos_result=[]
    for row in range(cell_gene_array_all.shape[0]):
        #print(cell_gene_array_all[row])
        row_result=''
        for col in range(cell_gene_array_all.shape[1]):
            if cell_gene_array_all[row][col]==True:
                row_result=row_result+'_'+gene_names[col]     
        #print(row_result)
        if row_result=='':
            row_result="All-neagtive"
        cell_pos_result.append(row_result.strip("_"))  
    adata.obs[obs_key]=cell_pos_result
    adata.obs[obs_key]=adata.obs[obs_key].astype('category')
    return adata


def rank_genes(adata,output_dir="./adata_output/",output_prefix="adata_",
               wilcox=True,logreg=True,t_test=True,rank_use_raw=True,obs_key="leiden",n_jobs=1,**parameters
                 ):
    """
    rank_genes(
    adata,
    output_dir="./adata_output/", # use same output_dir as in the parameters["output_dir"] used in MD_PP2C(adata,parameters)
    output_prefix="adata_",#######  use same output_prefix as in as in the parameters["output_prefix"] used in MD_PP2C(adata,parameters)
    wilcox=True,logreg=True,t_test=True, ####  which test to run 
    rank_use_raw=True, # if set to false only uses the highly varrible genes 
    obs_key="leiden", adata.obs key to use to find differentially expressed genes
    n_jobs=8 # number of threads
    returns rank_genes_groups_wilcox, rank_genes_groups_logreg,rank_genes_groups_t_test
    )
    """
    import os
    import numpy as np
    import pandas as pd
    import scanpy as sc
    sc.settings.verbosity = 1             # verbosity: errors (0), warnings (1), info (2), hints (3)
    sc.logging.print_header()
    sc.settings.set_figure_params(dpi=80, facecolor='white')
    sc.settings.n_jobs = int(n_jobs)  
    os.makedirs(output_dir+output_prefix, exist_ok=True)
    os.makedirs(output_dir+output_prefix+'/tables/', exist_ok=True)
    dataset_tables_output_directory=output_dir+output_prefix+'/tables/'
    os.makedirs(output_dir+output_prefix+'/figures/', exist_ok=True)
    dataset_figures_output_directory=output_dir+output_prefix+'/figures/'

    sc.settings.figdir=dataset_figures_output_directory
    rank_genes_groups_wilcox=pd.DataFrame()
    rank_genes_groups_logreg=pd.DataFrame()
    rank_genes_groups_t_test=pd.DataFrame()
    #bug work around found on github
    #needed for next cell to run
    adata.uns['log1p']["base"] = None
    if wilcox==True:
        #########################  Wilcox
        sc.tl.rank_genes_groups(adata, obs_key, method='wilcoxon', use_raw=rank_use_raw, key_added='wilcoxon')
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False, key='wilcoxon',
                                save=output_prefix+'wilcoxon_topgenes.pdf')

        result = adata.uns['wilcoxon']
        groups = result['names'].dtype.names
        rank_genes_groups_wilcox=pd.DataFrame(
            {group + '_' + key[:16]: result[key][group]
            for group in groups for key in ['names', 'scores','pvals','pvals_adj','logfoldchanges']})
        rank_genes_groups_wilcox.to_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_wilcox.csv")

        #########################  Wilcox
    if logreg==True:
        #########################  logical reggression
        sc.tl.rank_genes_groups(adata, obs_key, method='logreg',use_raw=rank_use_raw, key_added='logreg')
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False, key='logreg',
                                save=output_prefix+'logreg_topgenes.pdf' )

        rank_genes_groups_logreg=pd.DataFrame(adata.uns['logreg']['names'])

        rank_genes_groups_logreg.to_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_logreg.csv")

        #########################  logical reggression

    if t_test==True:                                
        ######################### t-test
        sc.tl.rank_genes_groups(adata, obs_key, method='t-test',use_raw=rank_use_raw, key_added='t-test')
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False,key='t-test',
                               save=output_prefix+'t_test_topgenes.pdf')
        result = adata.uns['t-test']
        groups = result['names'].dtype.names
        rank_genes_groups_t_test=pd.DataFrame(
            {group + '_' + key[:16]: result[key][group]
            for group in groups for key in ['names', 'scores','pvals','pvals_adj','logfoldchanges']})
        rank_genes_groups_t_test.to_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_t_test.csv")         
         ######################### t-test
    return rank_genes_groups_wilcox, rank_genes_groups_logreg,rank_genes_groups_t_test
            
def rank_genes_obscat1_vs_obscat2(adata,output_dir="./adata_output/",output_prefix="adata_",wilcox=True,logreg=True,t_test=True,rank_use_raw=True,n_jobs=1,
                                  obs_key="leiden",obscat1='0',obscat2='1',
                                    **parameters
                                    ):
    """
    rank_genes_obscat1_vs_obscat2(
    adata,
    output_dir="./adata_output/", # use same output_dir as in the parameters["output_dir"] used in MD_PP2C(adata,parameters)
    output_prefix="adata_",#######  use same output_prefix as in as in the parameters["output_prefix"] used in MD_PP2C(adata,parameters)
    wilcox=True,logreg=True,t_test=True, ####  which test to run 
    rank_use_raw=True, # if set to false only uses the highly varrible genes 
    n_jobs=8 # number of threads
    obs_key="leiden", adata.obs key to use to find differentially expressed genes
    obscat1='0' # diffenretioally expressed genes in adata[obs_key]=obscat1 vs adata[obs_key]=obscat2
    obscat2='1'
    returns rank_genes_groups_wilcox, rank_genes_groups_logreg,rank_genes_groups_t_test   
    )
    """
    import os
    import numpy as np
    import pandas as pd
    import scanpy as sc
    sc.settings.verbosity = 1             # verbosity: errors (0), warnings (1), info (2), hints (3)
    sc.logging.print_header()
    sc.settings.set_figure_params(dpi=80, facecolor='white')
    sc.settings.n_jobs = int(n_jobs)  

    os.makedirs(output_dir+output_prefix, exist_ok=True)


    os.makedirs(output_dir+output_prefix+'/tables/', exist_ok=True)
    dataset_tables_output_directory=output_dir+output_prefix+'/tables/'

    os.makedirs(output_dir+output_prefix+'/figures/', exist_ok=True)
    dataset_figures_output_directory=output_dir+output_prefix+'/figures/'

    sc.settings.figdir=dataset_figures_output_directory
    rank_genes_groups_wilcox=pd.DataFrame()
    rank_genes_groups_logreg=pd.DataFrame()
    rank_genes_groups_t_test=pd.DataFrame()
    #bug work around found on github
    #needed for next cell to run
    adata.uns['log1p']["base"] = None
    if wilcox==True:
        #########################  Wilcox
        sc.tl.rank_genes_groups(adata,obs_key, groups=[obscat1], reference=obscat2, method='wilcoxon', use_raw=rank_use_raw, key_added=f'wilcoxon_{obscat1}_ref_{obscat2}')
        #sc.tl.rank_genes_groups(adata, obs_key, method='wilcoxon', use_raw=rank_use_raw)
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False,key=f'wilcoxon_{obscat1}_ref_{obscat2}',
                                save=output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+'wilcoxon_topgenes.pdf')

        result = adata.uns[f'wilcoxon_{obscat1}_ref_{obscat2}']
        groups = result['names'].dtype.names
        rank_genes_groups_wilcox=pd.DataFrame(
            {group + '_' + key[:16]: result[key][group]
            for group in groups for key in ['names', 'scores','pvals','pvals_adj','logfoldchanges']})
        rank_genes_groups_wilcox.to_csv(dataset_tables_output_directory+output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+"rank_genes_groups_wilcox.csv")

        #########################  Wilcox
    if logreg==True:
        #########################  logical reggression
        sc.tl.rank_genes_groups(adata,obs_key, groups=[obscat1], reference=obscat2, method='logreg', use_raw=rank_use_raw, key_added=f'logreg_{obscat1}_ref_{obscat2}')
       # sc.tl.rank_genes_groups(adata, obs_key, method='logreg',use_raw=rank_use_raw)
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False, key=f'logreg_{obscat1}_ref_{obscat2}',
                                save=output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+'logreg_topgenes.pdf')

        rank_genes_groups_logreg=pd.DataFrame(adata.uns[f'logreg_{obscat1}_ref_{obscat2}']['names'])

        rank_genes_groups_logreg.to_csv(dataset_tables_output_directory+output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+"rank_genes_groups_logreg.csv")

        #########################  logical reggression

    if t_test==True:                                
        ######################### t-test
        sc.tl.rank_genes_groups(adata,obs_key, groups=[obscat1], reference=obscat2, method='t-test', use_raw=rank_use_raw, key_added=f't-test_{obscat1}_ref_{obscat2}')
        #sc.tl.rank_genes_groups(adata, obs_key, method='t-test',use_raw=rank_use_raw)
        sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False, key=f't-test_{obscat1}_ref_{obscat2}',
                               save=output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+'t_test_topgenes.pdf')
        result = adata.uns[f't-test_{obscat1}_ref_{obscat2}']
        groups = result['names'].dtype.names
        rank_genes_groups_t_test=pd.DataFrame(
            {group + '_' + key[:16]: result[key][group]
            for group in groups for key in ['names', 'scores','pvals','pvals_adj','logfoldchanges']})
        rank_genes_groups_t_test.to_csv(dataset_tables_output_directory+output_prefix+obs_key+'_'+obscat1+'_VS_'+obscat2+'_'+"rank_genes_groups_t_test.csv")    
    return rank_genes_groups_wilcox, rank_genes_groups_logreg,rank_genes_groups_t_test    


# write function for differential gene expression analysis between two groups defined by a categorical variable in adata.obs but dont use the sc.tl.rank_genes_groups function use the t-test function from scipy.stats and the statsmodels.stats.multitest.multipletests function to correct for multiple testing return a dataframe with the gene names, t-test p-value, t-test log fold change, and corrected p-value for each gene. have the function to use a specfic adata layer instead of the adata.X matrix
def diff_exp(adata, groupby, group1, group2, layer=None):
    """
    Parameters
    ----------
    adata : AnnData object
    groupby : str
        The key of the observation grouping to consider.
    group1 : str
        The name of the first group.
    group2 : str
        The name of the second group.
    layer : str, optional (default: None)
        The key of the layer to use. If not specified, defaults to adata.X.
    Returns
    -------
    A dataframe with the gene names, t-test p-value, t-test log fold change, and corrected p-value for each gene.
    """
    # import all the libraries need by this function above 
    import numpy as np
    from scipy import stats
    from statsmodels.stats.multitest import multipletests
    import pandas as pd
    # remove adata rows with a  expression of 0 in all smaples
    adata = adata[:,~np.all(adata.X == 0, axis=0)]
    # get the data matrix
    if layer is None:
        X = adata.X
    else:
        X = adata.layers[layer]
    
    # get the groupby categories
    cats = adata.obs[groupby].cat.categories
    # get the indices of the two groups
    idx1 = np.where(cats == group1)[0][0]
    idx2 = np.where(cats == group2)[0][0]
    # get the data for each group
    data1 = X[adata.obs[groupby] == group1, :]
    data2 = X[adata.obs[groupby] == group2, :]
    # get the p-values and log fold changes for each gene
    pvals = []
    logfc = []
    for i in range(data1.shape[1]):
        pvals.append(stats.ttest_ind(data1[:, i], data2[:, i])[1])
        #logfc.append(np.log2(np.mean(data1[:, i])) - np.log2(np.mean(data2[:, i])))
        logfc.append(np.log2(np.mean(data1[:, i]) / (np.mean(data2[:, i]))))
    # correct for multiple testing
    reject, pvals_corrected, _, _ = multipletests(pvals, method='fdr_bh')
    # return a dataframe with the results
    return pd.DataFrame({'gene': adata.var_names,
                         'pvals': pvals,
                         'pvals_corrected': pvals_corrected,
                         'logfc': logfc})



def GSEA_enrichr_all_clusters(output_dir="./adata_output/",output_prefix="adata_",
                              test_library_names=['GO_Biological_Process_2021','GO_Cellular_Component_2021','GO_Molecular_Function_2021'], top_nth=10,n_jobs=1,
                                **parameters
                                ):
    """This is the doc string
    This functions take the tables produced by the MD_rank_genes(adata,output_dir,output_prefix) function and perfroms GSEA analysis using the gseapy enrichr package 
    
    default arguements:
    MD_GSEA_enrichr_all_clusters(
    output_dir="./figures/", # set this to same output_dir used for MD_rank_genes(adata,output_dir,output_prefix)
    output_prefix="adata", # set this to same output_prefix directory used for MD_rank_genes(adata,output_dir,output_prefix)
    test_library_names=['GO_Biological_Process_2021','GO_Cellular_Component_2021','GO_Molecular_Function_2021'], # pick from list below
    top_nth=10, # set the top_nth percentile of the backgorund list to be used as the foregorund list 
    ##top_nth=10 (default) means the foregourd list is the top 10% of the background list
    )
    
    
    List of avalible gene sets to look for enrichement. These can go into  test_library_names=[] list .
      ['ARCHS4_Cell-lines',
     'ARCHS4_IDG_Coexp',
     'ARCHS4_Kinases_Coexp',
     'ARCHS4_TFs_Coexp',
     'ARCHS4_Tissues',
     'Achilles_fitness_decrease',
     'Achilles_fitness_increase',
     'Aging_Perturbations_from_GEO_down',
     'Aging_Perturbations_from_GEO_up',
     'Allen_Brain_Atlas_10x_scRNA_2021',
     'Allen_Brain_Atlas_down',
     'Allen_Brain_Atlas_up',
     'Azimuth_Cell_Types_2021',
     'BioCarta_2013',
     'BioCarta_2015',
     'BioCarta_2016',
     'BioPlanet_2019',
     'BioPlex_2017',
     'CCLE_Proteomics_2020',
     'CORUM',
     'COVID-19_Related_Gene_Sets',
     'COVID-19_Related_Gene_Sets_2021',
     'Cancer_Cell_Line_Encyclopedia',
     'CellMarker_Augmented_2021',
     'ChEA_2013',
     'ChEA_2015',
     'ChEA_2016',
     'Chromosome_Location',
     'Chromosome_Location_hg19',
     'ClinVar_2019',
     'DSigDB',
     'Data_Acquisition_Method_Most_Popular_Genes',
     'DepMap_WG_CRISPR_Screens_Broad_CellLines_2019',
     'DepMap_WG_CRISPR_Screens_Sanger_CellLines_2019',
     'Descartes_Cell_Types_and_Tissue_2021',
     'DisGeNET',
     'Disease_Perturbations_from_GEO_down',
     'Disease_Perturbations_from_GEO_up',
     'Disease_Signatures_from_GEO_down_2014',
     'Disease_Signatures_from_GEO_up_2014',
     'DrugMatrix',
     'Drug_Perturbations_from_GEO_2014',
     'Drug_Perturbations_from_GEO_down',
     'Drug_Perturbations_from_GEO_up',
     'ENCODE_Histone_Modifications_2013',
     'ENCODE_Histone_Modifications_2015',
     'ENCODE_TF_ChIP-seq_2014',
     'ENCODE_TF_ChIP-seq_2015',
     'ENCODE_and_ChEA_Consensus_TFs_from_ChIP-X',
     'ESCAPE',
     'Elsevier_Pathway_Collection',
     'Enrichr_Libraries_Most_Popular_Genes',
     'Enrichr_Submissions_TF-Gene_Coocurrence',
     'Enrichr_Users_Contributed_Lists_2020',
     'Epigenomics_Roadmap_HM_ChIP-seq',
     'FANTOM6_lncRNA_KD_DEGs',
     'GO_Biological_Process_2013',
     'GO_Biological_Process_2015',
     'GO_Biological_Process_2017',
     'GO_Biological_Process_2017b',
     'GO_Biological_Process_2018',
     'GO_Biological_Process_2021',
     'GO_Cellular_Component_2013',
     'GO_Cellular_Component_2015',
     'GO_Cellular_Component_2017',
     'GO_Cellular_Component_2017b',
     'GO_Cellular_Component_2018',
     'GO_Cellular_Component_2021',
     'GO_Molecular_Function_2013',
     'GO_Molecular_Function_2015',
     'GO_Molecular_Function_2017',
     'GO_Molecular_Function_2017b',
     'GO_Molecular_Function_2018',
     'GO_Molecular_Function_2021',
     'GTEx_Aging_Signatures_2021',
     'GTEx_Tissue_Expression_Down',
     'GTEx_Tissue_Expression_Up',
     'GWAS_Catalog_2019',
     'GeneSigDB',
     'Gene_Perturbations_from_GEO_down',
     'Gene_Perturbations_from_GEO_up',
     'Genes_Associated_with_NIH_Grants',
     'Genome_Browser_PWMs',
     'HDSigDB_Human_2021',
     'HDSigDB_Mouse_2021',
     'HMDB_Metabolites',
     'HMS_LINCS_KinomeScan',
     'HomoloGene',
     'HuBMAP_ASCT_plus_B_augmented_w_RNAseq_Coexpression',
     'HuBMAP_ASCTplusB_augmented_2022',
     'HumanCyc_2015',
     'HumanCyc_2016',
     'Human_Gene_Atlas',
     'Human_Phenotype_Ontology',
     'InterPro_Domains_2019',
     'Jensen_COMPARTMENTS',
     'Jensen_DISEASES',
     'Jensen_TISSUES',
     'KEA_2013',
     'KEA_2015',
     'KEGG_2013',
     'KEGG_2015',
     'KEGG_2016',
     'KEGG_2019_Human',
     'KEGG_2019_Mouse',
     'KEGG_2021_Human',
     'Kinase_Perturbations_from_GEO_down',
     'Kinase_Perturbations_from_GEO_up',
     'L1000_Kinase_and_GPCR_Perturbations_down',
     'L1000_Kinase_and_GPCR_Perturbations_up',
     'LINCS_L1000_Chem_Pert_down',
     'LINCS_L1000_Chem_Pert_up',
     'LINCS_L1000_Ligand_Perturbations_down',
     'LINCS_L1000_Ligand_Perturbations_up',
     'Ligand_Perturbations_from_GEO_down',
     'Ligand_Perturbations_from_GEO_up',
     'MCF7_Perturbations_from_GEO_down',
     'MCF7_Perturbations_from_GEO_up',
     'MGI_Mammalian_Phenotype_2013',
     'MGI_Mammalian_Phenotype_2017',
     'MGI_Mammalian_Phenotype_Level_3',
     'MGI_Mammalian_Phenotype_Level_4',
     'MGI_Mammalian_Phenotype_Level_4_2019',
     'MGI_Mammalian_Phenotype_Level_4_2021',
     'MSigDB_Computational',
     'MSigDB_Hallmark_2020',
     'MSigDB_Oncogenic_Signatures',
     'Microbe_Perturbations_from_GEO_down',
     'Microbe_Perturbations_from_GEO_up',
     'Mouse_Gene_Atlas',
     'NCI-60_Cancer_Cell_Lines',
     'NCI-Nature_2015',
     'NCI-Nature_2016',
     'NIH_Funded_PIs_2017_AutoRIF_ARCHS4_Predictions',
     'NIH_Funded_PIs_2017_GeneRIF_ARCHS4_Predictions',
     'NIH_Funded_PIs_2017_Human_AutoRIF',
     'NIH_Funded_PIs_2017_Human_GeneRIF',
     'NURSA_Human_Endogenous_Complexome',
     'OMIM_Disease',
     'OMIM_Expanded',
     'Old_CMAP_down',
     'Old_CMAP_up',
     'Orphanet_Augmented_2021',
     'PPI_Hub_Proteins',
     'PanglaoDB_Augmented_2021',
     'Panther_2015',
     'Panther_2016',
     'Pfam_Domains_2019',
     'Pfam_InterPro_Domains',
     'PheWeb_2019',
     'PhenGenI_Association_2021',
     'Phosphatase_Substrates_from_DEPOD',
     'ProteomicsDB_2020',
     'RNA-Seq_Disease_Gene_and_Drug_Signatures_from_GEO',
     'RNAseq_Automatic_GEO_Signatures_Human_Down',
     'RNAseq_Automatic_GEO_Signatures_Human_Up',
     'RNAseq_Automatic_GEO_Signatures_Mouse_Down',
     'RNAseq_Automatic_GEO_Signatures_Mouse_Up',
     'Rare_Diseases_AutoRIF_ARCHS4_Predictions',
     'Rare_Diseases_AutoRIF_Gene_Lists',
     'Rare_Diseases_GeneRIF_ARCHS4_Predictions',
     'Rare_Diseases_GeneRIF_Gene_Lists',
     'Reactome_2013',
     'Reactome_2015',
     'Reactome_2016',
     'SILAC_Phosphoproteomics',
     'SubCell_BarCode',
     'SysMyo_Muscle_Gene_Sets',
     'TF-LOF_Expression_from_GEO',
     'TF_Perturbations_Followed_by_Expression',
     'TG_GATES_2020',
     'TRANSFAC_and_JASPAR_PWMs',
     'TRRUST_Transcription_Factors_2019',
     'Table_Mining_of_CRISPR_Studies',
     'TargetScan_microRNA',
     'TargetScan_microRNA_2017',
     'Tissue_Protein_Expression_from_Human_Proteome_Map',
     'Tissue_Protein_Expression_from_ProteomicsDB',
     'Transcription_Factor_PPIs',
     'UK_Biobank_GWAS_v1',
     'Virus-Host_PPI_P-HIPSTer_2020',
     'VirusMINT',
     'Virus_Perturbations_from_GEO_down',
     'Virus_Perturbations_from_GEO_up',
     'WikiPathway_2021_Human',
     'WikiPathways_2013',
     'WikiPathways_2015',
     'WikiPathways_2016',
     'WikiPathways_2019_Human',
     'WikiPathways_2019_Mouse',
     'dbGaP',
     'huMAP',
     'lncHUB_lncRNA_Co-Expression',
     'miRTarBase_2017']
    """
    import scanpy as sc
    import pandas as pd
    import gseapy as gp
    import numpy as np
    import matplotlib.pyplot as plt
    import os
    ################## supress FutureWarning
    import warnings
    warnings.simplefilter(action='ignore', category=FutureWarning)
    ##################

    sc.settings.n_jobs = int(n_jobs)

    os.makedirs(output_dir+output_prefix, exist_ok=True)
    os.makedirs(output_dir+output_prefix+'/tables/', exist_ok=True)
    dataset_tables_output_directory=output_dir+output_prefix+'/tables/'
    os.makedirs(output_dir+output_prefix+'/figures/', exist_ok=True)
    dataset_figures_output_directory=output_dir+output_prefix+'/figures/'
    sc.settings.figdir=dataset_figures_output_directory
    os.makedirs(output_dir+output_prefix+"/GSEA_out/", exist_ok=True)
    dataset_GESA_output_directory=output_dir+output_prefix+"/GSEA_out/"

    #total_cluster_number=len(set(adata.obs['leiden'].tolist()))

    top_percentile=(top_nth)/100


    ############################## logical regression test GSEA
    test="logreg"
    full_table = pd.read_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_"+test+".csv",header=0,index_col=0)
    total_cluster_number=len(full_table.columns) # set total cluster number to column # of loreg rank table
    background_list_len=full_table.shape[0]
    print(f'logreg: the full_table  is {full_table.shape[0]} genes long by {full_table.shape[1]} columns for {total_cluster_number} clusters')
    foreground_list_len=len((full_table[ :int(background_list_len * top_percentile)]))
    print(f'logreg: the foreground list is {foreground_list_len} genes long')

    for i in range(0, total_cluster_number):
        test_cluster_number=i

        os.makedirs(dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number), exist_ok=True)
        cluster_gsea_output_dir=dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number)

        background_list=full_table[full_table.columns[test_cluster_number]].squeeze().str.strip().tolist()
        foreground_list=(background_list[ :int(background_list_len * top_percentile)])
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 background genes {background_list[:3]}, bottom 3 background genes {background_list[-3:]} ")
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 foreground genes {foreground_list[:3]}, bottom 3 foreground genes {foreground_list[-3:]} ")
        # run enrichr
        # list, dataframe, series inputs are supported
        try:
            enr = gp.enrichr(gene_list=foreground_list,
                         background=background_list,
                         gene_sets=test_library_names,
                         organism='Human', # don't forget to set organism to the one you desired! e.g. Yeast
                         #description=test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number),
                         outdir=cluster_gsea_output_dir,
                         # no_plot=True,
                         cutoff=1 # test dataset, use lower value from range(0,1)
                        )
        except Exception as e:
            print("Something went wrong "+ str(e))
    ############################## logical regression test GSEA END

    ############################## wilcox regression test GSEA
    test="wilcox"

    full_table = pd.read_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_"+test+".csv",header=0,index_col=0)
    total_cluster_number=int(len(full_table.columns)/5) # set total cluster number to column # / 4 of wilcox or t test rank table
    background_list_len=full_table.shape[0]
    print(f'wilcox: the full_table  is {full_table.shape[0]} genes long by {full_table.shape[1]} columns for {total_cluster_number} clusters')
    foreground_list_len=len((full_table[ :int(background_list_len * top_percentile)]))
    print(f'wilcox: the foreground list is {foreground_list_len} genes long')

    for i in range(0, total_cluster_number):
        test_cluster_number=i

        os.makedirs(dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number), exist_ok=True)
        cluster_gsea_output_dir=dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number)
        #background_list=full_table[full_table.columns[(test_cluster_number*2)]].tolist()
        #background_list=full_table[full_table.columns[(test_cluster_number*2)]].squeeze().str.strip().tolist()
        #background_list=full_table[full_table.columns[(test_cluster_number*5)]].squeeze().str.strip().tolist()
        #background_list=full_table[full_table.columns[(test_cluster_number*5)]].tolist()
        background_list=full_table[full_table.columns[(test_cluster_number*5)]].squeeze().str.strip().tolist()
        foreground_list=(background_list[ :int(background_list_len * top_percentile)])
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 background genes {background_list[:3]}, bottom 3 background genes {background_list[-3:]} ")
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 foreground genes {foreground_list[:3]}, bottom 3 foreground genes {foreground_list[-3:]} ")
        # run enrichr
        # list, dataframe, series inputs are supported
        try:
            enr = gp.enrichr(gene_list=foreground_list,
                             background=background_list,
                             gene_sets=test_library_names,
                             organism='Human', # don't forget to set organism to the one you desired! e.g. Yeast
                             #description=test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number),
                             outdir=cluster_gsea_output_dir,
                             # no_plot=True,
                             cutoff=1 # test dataset, use lower value from range(0,1)
                            )
        except Exception as e:
            print("Something went wrong "+ str(e))
    ############################## wilcox regression test GSEA END


    ############################## t_test regression test GSEA
    test="t_test"

    full_table = pd.read_csv(dataset_tables_output_directory+output_prefix+"rank_genes_groups_"+test+".csv",header=0,index_col=0)
    total_cluster_number=int(len(full_table.columns)/5) # set total cluster number to column # / 5 of wilcox or t test rank table
    background_list_len=full_table.shape[0]
    print(f'wilcox: the full_table  is {full_table.shape[0]} genes long by {full_table.shape[1]} columns for {total_cluster_number} clusters')
    foreground_list_len=len((full_table[ :int(background_list_len * top_percentile)]))
    print(f'wilcox: the foreground list is {foreground_list_len} genes long')

    for i in range(0, total_cluster_number):
        test_cluster_number=i

        os.makedirs(dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number), exist_ok=True)
        cluster_gsea_output_dir=dataset_GESA_output_directory+test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number)

        #background_list=full_table[full_table.columns[(test_cluster_number*2)]].squeeze().str.strip().tolist()
        background_list=full_table[full_table.columns[(test_cluster_number*5)]].squeeze().str.strip().tolist()
        foreground_list=(background_list[ :int(background_list_len * top_percentile)])
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 background genes {background_list[:3]}, bottom 3 background genes {background_list[-3:]} ")
        print(f"<CLUSTER {test_cluster_number}> for {test} gene rank top 3 foreground genes {foreground_list[:3]}, bottom 3 foreground genes {foreground_list[-3:]} ")
        # run enrichr
        # list, dataframe, series inputs are supported
        try:
                  enr = gp.enrichr(gene_list=foreground_list,
                         background=background_list,
                         gene_sets=test_library_names,
                         organism='Human', # don't forget to set organism to the one you desired! e.g. Yeast
                         #description=test+"_top_"+str(top_nth)+"pct_"+"cluster_"+str(test_cluster_number),
                         outdir=cluster_gsea_output_dir,
                         # no_plot=True,
                         cutoff=1 # test dataset, use lower value from range(0,1)
                        )
        except Exception as e:
            print("Something went wrong "+ str(e))
    ############################## t_test regression test GSEA END
    return
    
    